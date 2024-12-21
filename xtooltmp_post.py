#
#
#  CAM post processor to generate XTool Creative Space project file

#  leveraged from FreeCad/src/Mod/CAM/Path/Post/scripts/generic_post.py


import os
from Path.Post.Processor import PostProcessor
import Path
import FreeCAD
import Path.Post.Utils as PostUtils
import Path.Post.UtilsParse as PostUtilsParse
import Path.Tool.Controller as PathToolController

import argparse
from typing import Any, Dict, Union
import Path.Post.UtilsArguments as PostUtilsArguments
import Path.Post.UtilsExport as PostUtilsExport



Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

translate = FreeCAD.Qt.translate

debug = True
if debug:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


# Define some types that are used throughout this file
Parser = argparse.ArgumentParser
Values = Dict[str, Any]

#
# Default to metric mode
#
UNITS: str = "G21"

def init_values(values: Values) -> None:
    """Initialize values that are used throughout the postprocessor."""
    #
    PostUtilsArguments.init_shared_values(values)
    #
    # Set any values here that need to override the default values set
    # in the init_shared_values routine.
    #
    values["ENABLE_COOLANT"] = True
    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane; Arcs need work.
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
    values["MACHINE_NAME"] = "LinuxCNC"
    #
    # Any commands in this value will be output as the last commands
    # in the G-code file.
    #
    values[
        "POSTAMBLE"
    ] = """M05
G17 G54 G90 G80 G40
M2"""
    values["POSTPROCESSOR_FILE_NAME"] = __name__
    #
    # Any commands in this value will be output after the header and
    # safety block at the beginning of the G-code file.
    #
    values["PREAMBLE"] = """G17 G54 G40 G49 G80 G90"""
    values["UNITS"] = UNITS
def init_argument_defaults(argument_defaults: Dict[str, bool]) -> None:
    """Initialize which arguments (in a pair) are shown as the default argument."""
    PostUtilsArguments.init_argument_defaults(argument_defaults)
    #
    # Modify which argument to show as the default in flag-type arguments here.
    # If the value is True, the first argument will be shown as the default.
    # If the value is False, the second argument will be shown as the default.
    #
    # For example, if you want to show Metric mode as the default, use:
    #   argument_defaults["metric_inch"] = True
    #
    # If you want to show that "Don't pop up editor for writing output" is
    # the default, use:
    #   argument_defaults["show-editor"] = False.
    #
    # Note:  You also need to modify the corresponding entries in the "values" hash
    #        to actually make the default value(s) change to match.
    #


def init_arguments_visible(arguments_visible: Dict[str, bool]) -> None:
    """Initialize which argument pairs are visible in TOOLTIP_ARGS."""
    PostUtilsArguments.init_arguments_visible(arguments_visible)
    #
    # Modify the visibility of any arguments from the defaults here.
    #


def init_arguments(
    values: Values,
    argument_defaults: Dict[str, bool],
    arguments_visible: Dict[str, bool],
) -> Parser:
    """Initialize the shared argument definitions."""
    parser: Parser = PostUtilsArguments.init_shared_arguments(
        values, argument_defaults, arguments_visible
    )
    #
    # Add any argument definitions that are not shared with all other
    # postprocessors here.
    #
    return parser

#
# Creating global variables and using functions to modify them
# is useful for being able to test things later.
#
global_values: Values = {}
init_values(global_values)
global_argument_defaults: Dict[str, bool] = {}
init_argument_defaults(global_argument_defaults)
global_arguments_visible: Dict[str, bool] = {}
init_arguments_visible(global_arguments_visible)
global_parser: Parser = init_arguments(
    global_values, global_argument_defaults, global_arguments_visible
)
#
# The TOOLTIP_ARGS value is created from the help information about the arguments.
#
TOOLTIP_ARGS: str = global_parser.format_help()


#
# Create another parser just to get a list of all possible arguments
# that may be output using --output_all_arguments.
#
global_all_arguments_visible: Dict[str, bool] = {}
for k in iter(global_arguments_visible):
    global_all_arguments_visible[k] = True
global_all_visible: Parser = init_arguments(
    global_values, global_argument_defaults, global_all_arguments_visible
)



class Xtooltmp(PostProcessor):
    def __init__(self, job):
        super().__init__(
            job,
            tooltip=translate("CAM", "XTool XCS post processor"),
            tooltipargs=["arg1", "arg2"],
            units="kg",
        )
        Path.Log.debug("XTool XCS post processor initialized")

    def export(self):
        Path.Log.debug("Exporting the job")

        postables = self._buildPostList()
        Path.Log.debug(f"postables count: {len(postables)}")

        g_code_sections = []
        for idx, section in enumerate(postables):
            partname, sublist = section

            Path.Log.debug(f"partname: {partname}")
            gcode = self.export_xcs(sublist)

            # here is where the sections are converted to gcode.
            g_code_sections.append((idx, partname))

        return g_code_sections

    @property
    def tooltip(self):

        tooltip = """
        This is a XTool XCS post processor.
        It creates an XCS project file
        """
        return tooltip

    @property
    def tooltipArgs(self):
        argtooltip = """
        --arg1: This is the first argument
        --arg2: This is the second argument

        """
        return argtooltip

    @property
    def units(self):
        return self._units

    def export_xcs(self, objectlist):

        print(objectlist)
        print(self._args)

        filename = '-'

        args: Union[str, argparse.Namespace]
        flag: bool

        global UNITS  # pylint: disable=global-statement

        #print(parser.format_help())

        (flag, args) = PostUtilsArguments.process_shared_arguments(
            global_values, global_parser, self._args, global_all_visible, filename
        )
        if not flag:
            return args  # type: ignore
        #
        # Process any additional arguments here
        #

        #
        # Update the global variables that might have been modified
        # while processing the arguments.
        #
        UNITS = global_values["UNITS"]

        print("postprocessing...")
        gcode = ""
        svg = ""
    
        return gcode

    def linenumber(self):
        return ''
        return PostUtilsParse.linenumber()

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

