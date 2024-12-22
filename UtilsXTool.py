# ***************************************************************************
# *   Copyright (c) 2024 whodafloater
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# **************************************************************************
#
# Common functions for the XTool post processor
#    export_xtool() returns gcode and an xcs project
#
# parts leveraged from linuxcnc_post.py, refactored_linuxcnc_post.py
#    Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>
#    Copyright (c) 2022 Larry Woestman <LarryWoestman2@gmail.com>
#

import FreeCAD
from FreeCAD import Units
from FreeCAD import Vector
import Path.Post.UtilsArguments as PostUtilsArguments

import Path
import Path.Geom as PathGeom
import math

import xtool_xcs as xt

# needed for fclps() and svgnum()
PRECISION = ''
UNIT_FORMAT = ''

# p1, p2, c are vector objects
def gcode_arc(cmd, p1):
    p2 = PathGeom.commandEndPoint(cmd, p1)
    c  = p1 + PathGeom.commandEndPoint(cmd, Vector(0, 0, 0), "I", "J", "K")

    r1 = (p1 - c)
    r2 = (p2 - c)
    rad = r1.Length

    a1 = math.atan2(r1.y, r1.x)
    a2 = math.atan2(r2.y, r2.x)

    if cmd.Name in ['G3', 'G03',]:
        # CCW
        tarc = a2 - a1
        if tarc < 0:
            tarc += 2 * math.pi
    else:
        # CW
        tarc = a2 - a1
        if tarc > 0:
            tarc -= 2 * math.pi

    # chord_err = rad * (1 - cos(arcstep/2))
    # arcstep = 2 * acos(1 - chord_err / rad)
    chord_err = 0.01
    arcstep = 2 * math.acos(1 - chord_err / rad)

    n = int(abs(tarc / arcstep))
    n = max(n, 2)
    n = min(n, 128)
    segs = []
    for i in range(1, n):
        a = a1 + tarc * float(i) / float(n-1);
        x = c.x + rad * math.cos(a)
        y = c.y + rad * math.sin(a)
        segs.append(f'G1 X{fculps(x, "X")} Y{fculps(y, "Y")}')

    return segs


def svg_finish_path(dout, svg, feed, power, bound):
    # capture path only if it draws something
    if not "L" in svg:
        return

    dout['svgps'].append({'svg' : svg, 'feed' : feed, 'power' : power,
                          'xmin' : min(bound['x']),
                          'xmax' : max(bound['x']),
                          'ymin' : min(bound['y']),
                          'ymax' : max(bound['y']),
                        })

    # update the global bounding box
    tail = len(dout['svgps']) - 1
    dout['glob_bound']['x'].append(dout['svgps'][tail]['xmin'])
    dout['glob_bound']['x'].append(dout['svgps'][tail]['xmax'])
    dout['glob_bound']['y'].append(dout['svgps'][tail]['ymax'])
    dout['glob_bound']['y'].append(dout['svgps'][tail]['ymin'])

    print(dout['svgps'][tail])


def svg_move(cmd, startPoint, bound):
    endPoint = PathGeom.commandEndPoint(cmd, startPoint)
    return "M" + svgnum(endPoint.x) + " " + svgnum(-endPoint.y)


def svg_line(cmd, startPoint, bound):
    endPoint = PathGeom.commandEndPoint(cmd, startPoint)

    bound['x'].append(startPoint.x)
    bound['y'].append(-startPoint.y)
    bound['x'].append(endPoint.x)
    bound['y'].append(-endPoint.y)

    return " L" + svgnum(endPoint.x) + " " + svgnum(-endPoint.y)


# https://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes
# section B.2.3
# for vector class:
#   https://github.com/FreeCAD/FreeCAD/blob/master/src/Base/VectorPy.xml
#   https://github.com/FreeCAD/FreeCAD/blob/master/src/Base/VectorPyImp.cpp
#
# p1, p2, c are vector objects
def svg_arc(cmd, p1, bound):
    p2 = PathGeom.commandEndPoint(cmd, p1)
    c  = p1 + PathGeom.commandEndPoint(cmd, Vector(0, 0, 0), "I", "J", "K")

    r = (p1 - c)
    rad = svgnum(r.Length)
    ca = (c - p1).normalize()
    cb = (c - p2).normalize()

    # cross prod = mag(ra) * mag(rb) * sin( angle(bac) )
    cp = Vector.cross(ca, cb).z

    # four possible ways to "arc" from p1 to p2:
    # CCW, small angle, cp will be positive
    #      large angle, cp will be negative
    # CW,  small angle, cp will be negative
    #      large angle, cp will be positive

    # svg arc: A radx rady rot fa fs X Y
    #
    # svg arcs are elliptical.
    # rot is rotation of the ellipse
    #
    # four possible paths from p1 to p2
    # fa 1 large arc
    #    0 small arc
    # fs 1 sweep rigth, cw
    #    0 sweep left, ccw
    # note that the SVG plane is flipped about the x axis
    # so cw -> ccw, ccw -> cw

    #  A radx rady
    s = " A" + " " + rad + " " + rad

    # rot fa fs
    # rot is always 0 since we do circles only
    if cmd.Name in ['G3', 'G03',]:
        # CW because Y-axis is inverted for svg
        if(cp > 0):
           s += " 0 0 0 "
        else:
           s += " 0 1 0 "
    else:
        # CCW because Y-axis is inverted for svg
        if(cp < 0):
           s += " 0 0 1 "
        else:
           s += " 0 1 1 "

    #  x y
    s += svgnum(p2.x) + " " + svgnum(-p2.y)

    # -------------------
    # bounding box
    x = Vector(1,0,0)
    y = Vector(0,1,0)
    if cmd.Name in ['G3', 'G03',]:
        # CW because Y-axis is inverted for svg
        aax = cb.getAngle(x)
        abx = ca.getAngle(x)
        aay = cb.getAngle(y)
        aby = ca.getAngle(y)
    else:
        # CCW because Y-axis is inverted for svg
        aax = ca.getAngle(x)
        abx = cb.getAngle(x)
        aay = ca.getAngle(y)
        aby = cb.getAngle(y)

    if(aax <= 0 and abx >= 0 ):
        xmax = 1
    else:
        xmax = max(ca.dot(x), cb.dot(x))

    if(aax >= 0 and abx >= 0 ):
        xmin = -1
    else:
        xmin = min(ca.dot(x), cb.dot(x))

    if(aay <= 0 and aby >= 0 ):
        ymax = 1
    else:
        ymax = max(ca.dot(y), cb.dot(y))

    if(aay >= 0 and aby >= 0 ):
        ymin = -1
    else:
        ymin = min(ca.dot(y), cb.dot(y))

    bound['x'].append(xmin * r.Length + c.x)
    bound['x'].append(xmax * r.Length + c.x)
    bound['y'].append(-ymin * r.Length + -c.y)
    bound['y'].append(-ymax * r.Length + -c.y)
    # -------------------

    # debug, just a line
    #s = " L" + svgnum(p2.x) + " " + svgnum(p2.y)
    return s

def svgnum(val):
    global PRECISION
    global UNIT_FORMAT
    precision_string = "." + str(PRECISION) + "f"
    pos = Units.Quantity(val, FreeCAD.Units.Length)
    return format( float(pos.getValueAs(UNIT_FORMAT)), precision_string)

def fculps(val, key):
    global PRECISION
    global UNIT_FORMAT
    precision_string = "." + str(PRECISION) + "f"
    pos  = Units.Quantity(val, FreeCAD.Units.Length)
    if key == 'Y':
       pos = -pos
    return format(float(pos.getValueAs(UNIT_FORMAT)), precision_string)

def linenumber(values):
    LINENR = values["LINENR"]
    if values["OUTPUT_LINE_NUMBERS"] is True:
        LINENR += 10
        return "N" + str(LINENR) + " "
    values["LINENR"] = LINENR
    return ""

#def init_xtool_values(values: Values) -> None:
def init_xtool_values(values):
    """Initialize values that are used throughout the postprocessor."""
    #
    # See FreeCAD/src/Mod/Path/Path/Post/UtilsArguments.py
    # for common args and default values
    PostUtilsArguments.init_shared_values(values)
    #
    # Set any values here that need to override the default values set
    # in the init_shared_values routine.
    #
    # these are the linuxcnc values
    values["PARAMETER_ORDER"] = [
        "X",
        "Y",
        "Z",
        "A",
        "B",
        "C",
        "I",
        "J",
        "F",
        "S",
        "T",
        "Q",
        "R",
        "L",
        "H",
        "D",
        "P",
    ]
    #
    # Used in the argparser code as the "name" of the postprocessor program.
    # This would normally show up in the usage message in the TOOLTIP_ARGS,
    # but we are suppressing the usage message, so it doesn't show up after all.
    #
    values["MACHINE_NAME"] = "XTool D1"

    #
    # Any commands in this value will be output after the header and
    # safety block at the beginning of the G-code file.
    #

    # G92 X17 Y1   offset of the laser relative to the LED cross hair
    # G90          use absolute positioning
    # Now G1, G0 moves subract 17mm, 1mm from x,y in command so
    # led cross hair location is the effective 0,0
    values["PREAMBLE"] = """
M17 S1 (enable steppers)
M106 S0 (led off)
M205 X426 Y403
M101
G92 X17 Y1 (laser offset from led)
G90

G1 F1860
G0 F3000
G1 S020
"""

    # move to position that puts LED cross hair back to 0,0
    # turn on the cross hair to verify it is indeed back at 0,0
    # disable the steppers
    values[ "POSTAMBLE" ] = """
G0 X17 Y1
M106 S1 (led on)
M18 (disable steppers)
"""

    # What the machine wants. Don't change these.
    # Your FreeCAD drawing gets converted to these units in the gcode and svg.
    values["UNITS"] = "G21"  # G21 for metric, G20 for us standard
    values["UNIT_SPEED_FORMAT"] = "mm/min"
    values["UNIT_FORMAT"] = "mm"

    values["POSTPROCESSOR_FILE_NAME"] = __name__

    values["LINENR"] = 100

    # needed for fclps() and svgnum()
    global PRECISION
    global UNIT_FORMAT
    PRECISION = values["AXIS_PRECISION"]
    UNIT_FORMAT = values["UNIT_FORMAT"]


def export_xtool(values, objectslist, filename):

    # This is from the original xtool_xcs_post.py
    # Many fragments in here can migrate to the routines in UtilsExport.py

    OUTPUT_HEADER = values["OUTPUT_HEADER"]
    OUTPUT_COMMENTS = values["OUTPUT_COMMENTS"]
    UNIT_SPEED_FORMAT = values["UNIT_SPEED_FORMAT"]
    UNITS = values["UNITS"]
    PRE_OPERATION = values["PRE_OPERATION"]
    POST_OPERATION = values["POST_OPERATION"]
    POSTAMBLE = values["POSTAMBLE"]

    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print(
                "the object "
                + obj.Name
                + " is not a path. Please select only path and Compounds."
            )
            return None

    print("postprocessing...")
    gcode = ""
    svg = ""

    # write header
    if OUTPUT_HEADER:
        gcode += linenumber(values) + "(Exported by FreeCAD)\n"
        gcode += linenumber(values) + "(Post Processor: " + __name__ + ")\n"
        #gcode += linenumber(values) + "(Output Time:" + str(now) + ")\n"

    # Write the preamble
    if OUTPUT_COMMENTS:
        gcode += linenumber(values) + "(begin preamble)\n"
    for line in values["PREAMBLE"].splitlines(False):
        gcode += linenumber(values) + line + "\n"
    gcode += linenumber(values) + UNITS + "\n"

    dout = dict()
    dout['gcode'] = ""
    dout['svgps'] = list()
    dout['speed'] = 0
    dout['feed'] = 0
    dout['glob_bound'] = dict()
    dout['glob_bound']['x'] = list()
    dout['glob_bound']['y'] = list()

    for obj in objectslist:

        # Skip inactive operations
        if hasattr(obj, "Active"):
            if not obj.Active:
                continue
        if hasattr(obj, "Base") and hasattr(obj.Base, "Active"):
            if not obj.Base.Active:
                continue

        # do the pre_op
        if OUTPUT_COMMENTS:
            gcode += linenumber(values) + "(begin operation: %s)\n" % obj.Label
            gcode += linenumber(values) + "(machine units: %s)\n" % (UNIT_SPEED_FORMAT)
        for line in PRE_OPERATION.splitlines(True):
            gcode += linenumber(values) + line

        # get coolant mode
        coolantMode = "None"
        if (
            hasattr(obj, "CoolantMode")
            or hasattr(obj, "Base")
            and hasattr(obj.Base, "CoolantMode")
        ):
            if hasattr(obj, "CoolantMode"):
                coolantMode = obj.CoolantMode
            else:
                coolantMode = obj.Base.CoolantMode

        # turn coolant on if required
        if OUTPUT_COMMENTS:
            if not coolantMode == "None":
                gcode += linenumber(values) + "(Coolant On:" + coolantMode + ")\n"
        if coolantMode == "Flood":
            gcode += linenumber(values) + "M8" + "\n"
        if coolantMode == "Mist":
            gcode += linenumber(values) + "M7" + "\n"

        # process the operation gcode

        dout['gcode'] = ""
        dout['svgps'] = list()
        parse(values, dout, obj)

        gcode += dout['gcode']
        svgps = dout['svgps']

        # do the post_op
        if OUTPUT_COMMENTS:
            gcode += linenumber(values) + "(finish operation: %s)\n" % obj.Label
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber(values) + line

        # turn coolant off if required
        if not coolantMode == "None":
            if OUTPUT_COMMENTS:
                gcode += linenumber(values) + "(Coolant Off:" + coolantMode + ")\n"
            gcode += linenumber(values) + "M9" + "\n"

    # do the post_amble
    if OUTPUT_COMMENTS:
        gcode += "(begin postamble)\n"
    for line in POSTAMBLE.splitlines(True):
        gcode += linenumber(values) + line

    if False and FreeCAD.GuiUp and SHOW_EDITOR:
        final_gcode = gcode
        if len(gcode) > 100000:
            print("Skipping editor since output is greater than 100kb")
        else:
            #dia = PostUtils.GCodeEditorDialog()
            dia.editor.setText(gcode)
            result = dia.exec_()
            if result:
                final_gcode = dia.editor.toPlainText()
    else:
        final_gcode = gcode


#    if not filename == "-":
#        gfile = pythonopen(filename, "w")
#        gfile.write(final_gcode)
#        gfile.close()

    #print(svg)
    #print(svgps)

    gxmin = min(dout['glob_bound']['x'])
    gxmax = max(dout['glob_bound']['x'])
    gymin = min(dout['glob_bound']['y'])
    gymax = max(dout['glob_bound']['y'])

    print("x range: " + str(gxmin) + '  ' + str(gxmax))
    print("y range: " + str(gymin) + '  ' + str(gymax))

    svg = svgps[0]['svg']

    xt.XcsCanvas.canvi = list()
    canvas1 = xt.XcsCanvas();

    for p in svgps:
        print(p)

        pa = xt.XcsPath('path').setpath(0, 0, p['svg'])

        # svg paths are place relative to upper left of their bounding
        # box. This puts group bounding box at 0,0 (upper left)
        pa.place(-gxmin + p['xmin'], -gymin + p['ymin'])

        power = int(p['power']/10)
        feed = int(p['feed']/60)

        pa.add_process('VECTOR_CUTTING', power, feed, 1).group(filename)
        canvas1.add_element(pa);

    # In FreeCAD 1.0 we do not get a filename, just a '-'.
    # Just return serialized xcs json
   
    # FreeCAD 0.21 and before:
    # Save a xcs file as a side effect and return the gcode 
#    if not filename == '-':
#       # strip filename extension if it looks like gcode.
#       # XcsSave will add an xcs extensiont
#       print(f'incoming filename is {filename}')
#       f = filename.split('.')
#       if f[len(f)-1] in ['gc', 'gcode']:
#           f.pop(len(f)-1)
#       filename = '.'.join(f)
#
#       #filename = 'tmp.xcs'
#
#       xt.XcsCanvas.active_canvas = canvas1
#       print(f'saving to {filename}')
#       xt.XcsSave(filename)
#
#       print("done postprocessing.")
#       # return gcode
#       return final_gcode

    xt.XcsCanvas.active_canvas = canvas1
    xcs = xt.XcsSave('-')

    print("done postprocessing.")

    return final_gcode, xcs


def parse(values, dout, pathobj):
    # This is from the original xtool_xcs_post.py
    # Many fragments in here can migriate to the routines in UtilsExport.py

    OUTPUT_COMMENTS = values["OUTPUT_COMMENTS"]
    UNIT_SPEED_FORMAT = values["UNIT_SPEED_FORMAT"]
    OUTPUT_DOUBLES = values["OUTPUT_DOUBLES"]
    MODAL = values["MODAL"]
    AXIS_PRECISION = values["AXIS_PRECISION"]
    COMMAND_SPACE = values["COMMAND_SPACE"]
    OUTPUT_LINE_NUMBERS = values["OUTPUT_LINE_NUMBERS"]

    print('---------- parse ------------ feed=' + str(dout['feed']) + ' speed=' + str(dout['speed']))
    out = ""
    svg = ""
    svgps = list()

    svg_feed = dout['feed']
    svg_power = dout['speed']

    bound = dict()
    bound['x'] = list()
    bound['y'] = list()

    lastcommand = None
    precision_string = "." + str(AXIS_PRECISION) + "f"
    currLocation = {}  # keep track for no doubles
    prevLocation = {}

    RAPID_MOVES = ["G0", "G00"]
    FEED_MOVES = ["G1", "G01", "G2", "G02", "G3", "G03"]

    # the order of parameters
    params = values["PARAMETER_ORDER"]

    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters
    prevLocation.update(firstmove.Parameters)  # set First location Parameters

    start_path = False
    pathing = False
    finish_path = False

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        # if OUTPUT_COMMENTS:
        #     out += linenumber(values) + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            parse(dout, p)

        return

    else:  # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            #return out
            return dict(gcode = out, svgs = svgs)

        # if OUTPUT_COMMENTS:
        #     out += linenumber(values) + "(" + pathobj.Label + ")\n"

        for c in pathobj.Path.Commands:

            outstring = []
            command = c.Name
            outstring.append(command)

            # if modal: suppress the command if it is the same as the last one
            if MODAL is True:
                if command == lastcommand:
                    outstring.pop(0)

            if c.Name[0] == "(" and not OUTPUT_COMMENTS:  # command is a comment
                continue

            #print(str(prevLocation))
            #print(str(currLocation))
            print(c.Name + str(c.Parameters))

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == "F":
                        feed_rate = Units.Quantity(
                            c.Parameters["F"], FreeCAD.Units.Velocity
                           )

                        if feed_rate.getValueAs(UNIT_SPEED_FORMAT) > 0.0:
                            outstring.append(
                                param
                                + format(
                                    float(feed_rate.getValueAs(UNIT_SPEED_FORMAT)),
                                    precision_string,
                                )
                            )

                        dout['feed'] = feed_rate.getValueAs(UNIT_SPEED_FORMAT)

                    elif param == "T":
                        outstring.append(param + str(int(c.Parameters["T"])))
                    elif param == "H":
                        outstring.append(param + str(int(c.Parameters["H"])))
                    elif param == "D":
                        outstring.append(param + str(int(c.Parameters["D"])))
                    elif param == "S":
                        outstring.append(param + str(int(c.Parameters["S"])))
                        dout['speed'] = int(c.Parameters["S"])
                        print("new speed = " + str(dout['speed']))
                    else:
                        if (
                            (not OUTPUT_DOUBLES)
                            and (param in currLocation)
                            and (currLocation[param] == c.Parameters[param])
                        ):
                            continue
                        else:
                            # X20.123
                            # Y12.567
                            outstring.append(param + fculps(c.Parameters[param], param))

            arc_segs = []
            if c.Name in ["G2", "G02", "G3", "G03",]:
                arc_segs = gcode_arc(c, prevVector)
                outstring = []

            # store the latest command
            lastcommand = command
            currLocation.update(c.Parameters)
            currVector = Vector(currLocation["X"], currLocation["Y"], 0)

            # svg
            # start a new path if z step down

            if dout['speed'] != svg_power or dout['feed'] != svg_feed:
                if pathing:
                    print("speed or feed change: power=" + str(dout['speed']) + " feed=" +  str(dout['feed']))
                    finish_path = True

            if currLocation["Z"] > prevLocation["Z"]:
                if pathing:
                    print("Z up")
                    finish_path = True

            if currLocation["Z"] < prevLocation["Z"] and c.Name in FEED_MOVES:
                if not pathing:
                    start_path = True

            if pathing and finish_path:
                # start a new svg path. Only save current one if it draws something
                svg_finish_path(dout, svg, svg_feed, svg_power, bound)
                svg = ""
                svg_feed = dout['feed']
                svg_power = dout['speed']
                print("finish path, power = " + str(svg_power))
                finish_path = False
                pathing = False


            if start_path:
                print("start path: power=" + str(dout['speed']) + " feed=" +  str(dout['feed']))
                svg += svg_move(c, prevVector, bound)
                start_path = False
                pathing = True
                svg_feed = dout['feed']
                svg_power = dout['speed']
                bound['x'] = list()
                bound['y'] = list()


            if pathing and c.Name in FEED_MOVES:
                #print("pathing ...")
                if   c.Name in ["G1", "G01",]:
                    svg += svg_line(c, prevVector, bound)
                elif c.Name in ["G2", "G02", "G3", "G03",]:
                    svg += svg_arc(c, prevVector, bound)

            prevLocation.update(c.Parameters)
            prevVector = Vector(prevLocation["X"], prevLocation["Y"], 0)


            if command == "message":
                if OUTPUT_COMMENTS is False:
                    out = []
                else:
                    outstring.pop(0)  # remove the command

            # prepend a line number and append a newline
            if len(outstring) >= 1:
                if OUTPUT_LINE_NUMBERS:
                    outstring.insert(0, (linenumber(values)))

                # append the line to the final output
                for w in outstring:
                    out += w + COMMAND_SPACE
                # Note: Do *not* strip `out`, since that forces the allocation
                # of a contiguous string & thus quadratic complexity.
                out += "\n"

            if len(arc_segs) > 0:
                for w in arc_segs:
                    if OUTPUT_LINE_NUMBERS:
                        w.insert(0, (linenumber(values)))
                    out += w + "\n"

        svg_finish_path(dout, svg, svg_feed, svg_power, bound)

        dout['gcode'] = dout['gcode'] + out
        return dout


