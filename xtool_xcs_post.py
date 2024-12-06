#  Much of this code is leveraged from,
#     FreeCAD/src/Mod/CAM/Path/Post/scripts/linuxcnc_post.py
#
# ***************************************************************************
# *   Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>               *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************
#
#  Additional code to support XTool D1 gcode and XTool Creative Space project
#  file generation
#
#  Copyright (c) 2024 whodafloater
#

from __future__ import print_function
import FreeCAD
from FreeCAD import Units
from FreeCAD import Vector
import Path
import argparse
import datetime
import shlex

# FreeCAD 0.20
#from PathScripts import PostUtils
#import PathScripts.PathGeom as PathGeom

# FreeCAD 0.21
import Path.Geom as PathGeom

import xtool_xcs as xt
import json
import math

TOOLTIP = """
This is a postprocessor file for the Path workbench.
It produces:
   GCode file suitable for the xTool D1 Laser cutter
   An xcs project file for xTool Creative Space

SpindleSpeed is mapped to laser power, 1000RPM -> 100%

1/15/2023 GCode files must be manually copied to flash card as "tmp.gcode"
          xTool D1 does not support G2, G3 arcs. This post processor
          converts them to paths.

Best to use xTool Creative Space to interface with the machine.
"""

now = datetime.datetime.now()

parser = argparse.ArgumentParser(prog="linuxcnc", add_help=False)
parser.add_argument("--no-header", action="store_true", help="suppress header output")
parser.add_argument(
    "--no-comments", action="store_true", help="suppress comment output"
)
parser.add_argument(
    "--line-numbers", action="store_true", help="prefix with line numbers"
)
parser.add_argument(
    "--no-show-editor",
    action="store_true",
    help="don't pop up editor before writing output",
)
parser.add_argument(
    "--precision", default="3", help="number of digits of precision, default=3"
)
parser.add_argument(
    "--preamble",
    help='set commands to be issued before the first command, default="G17\nG90"',
)
parser.add_argument(
    "--postamble",
    help='set commands to be issued after the last command, default="M05\nG17 G90\nM2"',
)
parser.add_argument(
    "--inches", action="store_true", help="Convert output for US imperial mode (G20)"
)
parser.add_argument(
    "--modal",
    action="store_true",
    help="Output the Same G-command Name USE NonModal Mode",
)
parser.add_argument(
    "--axis-modal", action="store_true", help="Output the Same Axis Value Mode"
)
parser.add_argument(
    "--no-tlo",
    action="store_true",
    help="suppress tool length offset (G43) following tool changes",
)

TOOLTIP_ARGS = parser.format_help()

# These globals set common customization preferences
OUTPUT_COMMENTS = True
OUTPUT_HEADER = True
OUTPUT_LINE_NUMBERS = False
SHOW_EDITOR = True
MODAL = False  # if true commands are suppressed if the same as previous line.
USE_TLO = True  # if true G43 will be output following tool changes
OUTPUT_DOUBLES = (
    True  # if false duplicate axis values are suppressed if the same as previous line.
)
COMMAND_SPACE = " "
LINENR = 100  # line number starting value

# These globals will be reflected in the Machine configuration of the project
UNITS = "G21"  # G21 for metric, G20 for us standard
UNIT_SPEED_FORMAT = "mm/min"
UNIT_FORMAT = "mm"

MACHINE_NAME = "X-TOOL D1"
CORNER_MIN = {"x": 0, "y": 0, "z": 0}
CORNER_MAX = {"x": 500, "y": 300, "z": 300}
PRECISION = 3

# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = """
M17 S1
M106 S0
M205 X426 Y403
M101
G92 X17 Y1
G90

G1 F1860
G0 F3000
G1 S020
"""

# Postamble text will appear following the last operation.
POSTAMBLE = """
G0 X17 Y1
M18
"""

# Pre operation text will be inserted before every operation
PRE_OPERATION = """"""

# Post operation text will be inserted after every operation
POST_OPERATION = """"""

# Tool Change commands will be inserted before a tool change
TOOL_CHANGE = """"""

# to distinguish python built-in open function from the one declared below
if open.__module__ in ["__builtin__", "io"]:
    pythonopen = open

def processArguments(argstring):
    global OUTPUT_HEADER
    global OUTPUT_COMMENTS
    global OUTPUT_LINE_NUMBERS
    global SHOW_EDITOR
    global PRECISION
    global PREAMBLE
    global POSTAMBLE
    global UNITS
    global UNIT_SPEED_FORMAT
    global UNIT_FORMAT
    global MODAL
    global USE_TLO
    global OUTPUT_DOUBLES

    try:
        args = parser.parse_args(shlex.split(argstring))
        if args.no_header:
            OUTPUT_HEADER = False
        if args.no_comments:
            OUTPUT_COMMENTS = False
        if args.line_numbers:
            OUTPUT_LINE_NUMBERS = True
        if args.no_show_editor:
            SHOW_EDITOR = False
        print("Show editor = %d" % SHOW_EDITOR)
        PRECISION = args.precision
        if args.preamble is not None:
            PREAMBLE = args.preamble
        if args.postamble is not None:
            POSTAMBLE = args.postamble
        if args.inches:
            UNITS = "G20"
            UNIT_SPEED_FORMAT = "in/min"
            UNIT_FORMAT = "in"
            PRECISION = 4
        if args.modal:
            MODAL = True
        if args.no_tlo:
            USE_TLO = False
        if args.axis_modal:
            print("here")
            OUTPUT_DOUBLES = False

    except Exception:
        return False

    return True


def export(objectslist, filename, argstring):
    if not processArguments(argstring):
        return None
    global UNITS
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT

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
        gcode += linenumber() + "(Exported by FreeCAD)\n"
        gcode += linenumber() + "(Post Processor: " + __name__ + ")\n"
        gcode += linenumber() + "(Output Time:" + str(now) + ")\n"

    # Write the preamble
    if OUTPUT_COMMENTS:
        gcode += linenumber() + "(begin preamble)\n"
    for line in PREAMBLE.splitlines(False):
        gcode += linenumber() + line + "\n"
    gcode += linenumber() + UNITS + "\n"

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
            gcode += linenumber() + "(begin operation: %s)\n" % obj.Label
            gcode += linenumber() + "(machine units: %s)\n" % (UNIT_SPEED_FORMAT)
        for line in PRE_OPERATION.splitlines(True):
            gcode += linenumber() + line

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
                gcode += linenumber() + "(Coolant On:" + coolantMode + ")\n"
        if coolantMode == "Flood":
            gcode += linenumber() + "M8" + "\n"
        if coolantMode == "Mist":
            gcode += linenumber() + "M7" + "\n"

        # process the operation gcode

        dout['gcode'] = ""
        dout['svgps'] = list()
        parse(dout, obj)

        gcode += dout['gcode']
        svgps = dout['svgps']

        # do the post_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + "(finish operation: %s)\n" % obj.Label
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber() + line

        # turn coolant off if required
        if not coolantMode == "None":
            if OUTPUT_COMMENTS:
                gcode += linenumber() + "(Coolant Off:" + coolantMode + ")\n"
            gcode += linenumber() + "M9" + "\n"

    # do the post_amble
    if OUTPUT_COMMENTS:
        gcode += "(begin postamble)\n"
    for line in POSTAMBLE.splitlines(True):
        gcode += linenumber() + line

    if False and FreeCAD.GuiUp and SHOW_EDITOR:
        final = gcode
        if len(gcode) > 100000:
            print("Skipping editor since output is greater than 100kb")
        else:
            #dia = PostUtils.GCodeEditorDialog()
            dia.editor.setText(gcode)
            result = dia.exec_()
            if result:
                final = dia.editor.toPlainText()
    else:
        final = gcode


    if not filename == "-":
        gfile = pythonopen(filename, "w")
        gfile.write(final)
        gfile.close()

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
        #print(p)

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
    # Save a xcs file and return the gcode 
    if not filename == '-':
       # strip filename extension if it looks like gcode.
       # XcsSave will add an xcs extensiont
       print(f'incoming filename is {filename}')
       f = filename.split('.')
       if f[len(f)-1] in ['gc', 'gcode']:
           f.pop(len(f)-1)
       filename = '.'.join(f)

       #filename = 'tmp.xcs'

       xt.XcsCanvas.active_canvas = canvas1
       print(f'saving to {filename}')
       xt.XcsSave(filename)

       print("done postprocessing.")
       # return gcode
       return final

    print("done postprocessing.")
    xt.XcsCanvas.active_canvas = canvas1
    return xt.XcsSave('-')


def linenumber():
    global LINENR
    if OUTPUT_LINE_NUMBERS is True:
        LINENR += 10
        return "N" + str(LINENR) + " "
    return ""

def parse(dout, pathobj):
    global PRECISION
    global MODAL
    global OUTPUT_DOUBLES
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT

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
    precision_string = "." + str(PRECISION) + "f"
    currLocation = {}  # keep track for no doubles
    prevLocation = {}

    RAPID_MOVES = ["G0", "G00"]
    FEED_MOVES = ["G1", "G01", "G2", "G02", "G3", "G03"]

    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane  Arcs need work.
    params = [
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
    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters
    prevLocation.update(firstmove.Parameters)  # set First location Parameters

    start_path = False
    pathing = False
    finish_path = False

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            parse(dout, p)

        return

    else:  # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            #return out
            return dict(gcode = out, svgs = svgs)

        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(" + pathobj.Label + ")\n"

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
                    outstring.insert(0, (linenumber()))

                # append the line to the final output
                for w in outstring:
                    out += w + COMMAND_SPACE
                # Note: Do *not* strip `out`, since that forces the allocation
                # of a contiguous string & thus quadratic complexity.
                out += "\n"

            if len(arc_segs) > 0:
                for w in arc_segs:
                    if OUTPUT_LINE_NUMBERS:
                        w.insert(0, (linenumber()))
                    out += w + "\n"

        svg_finish_path(dout, svg, svg_feed, svg_power, bound)

        dout['gcode'] = dout['gcode'] + out
        return dout

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
    precision_string = "." + str(PRECISION) + "f"
    pos = Units.Quantity(val, FreeCAD.Units.Length)
    return format( float(pos.getValueAs(UNIT_FORMAT)), precision_string)

def fculps(val, key):
    global PRECISION
    precision_string = "." + str(PRECISION) + "f"
    pos  = Units.Quantity(val, FreeCAD.Units.Length)
    if key == 'Y':
       pos = -pos
    return format(float(pos.getValueAs(UNIT_FORMAT)), precision_string)


# print(__name__ + " gcode postprocessor loaded.")
