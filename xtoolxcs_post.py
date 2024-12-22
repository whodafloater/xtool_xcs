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
# boiler plate code leveraged from refactored_linuxcnc_post.py
#    Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>
#    Copyright (c) 2022 Larry Woestman <LarryWoestman2@gmail.com>

#
# export() is a wrapper for xtool_export() , returning just the gcode

# 
# start from refactored_linxcnc_post.y

import argparse

from typing import Any, Dict, Union

import Path.Post.UtilsArguments as PostUtilsArguments
import Path.Post.UtilsExport as PostUtilsExport
import Path
from FreeCAD import Vector
from importlib import reload

import UtilsXTool

# Define some types that are used throughout this file
Parser = argparse.ArgumentParser
Values = Dict[str, Any]

#
# The following variables need to be global variables
# to keep the PathPostProcessor.load method happy:
#
#    TOOLTIP
#    TOOLTIP_ARGS
#    UNITS
#
#    The "argument_defaults", "arguments_visible", and the "values" hashes
#    need to be defined before the "init_shared_arguments" routine can be
#    called to create TOOLTIP_ARGS, so they also end up having to be globals.
#
TOOLTIP: str = """This is a postprocessor file for the CAM workbench. It is used to
take a pseudo-gcode fragment outputted by a Path object, and output an XTool
Creative Space project file. This postprocessor, once placed in the appropriate
PathScripts folder, can be used directly from inside FreeCAD, via the GUI
importer or via python scripts with:

import xtoolxcs_post
xtoolxcs_post.export(object,"/path/to/file.ncc","")
"""

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
exec("reload(%s)" % "UtilsXTool")
UtilsXTool.init_xtool_values(global_values)

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

def export(objectslist, filename: str, argstring: str) -> str:
    """Postprocess the objects in objectslist to filename."""

    args: Union[str, argparse.Namespace]
    flag: bool

    (flag, args) = PostUtilsArguments.process_shared_arguments(
        global_values, global_parser, argstring, global_all_visible, filename
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

    gcode, xcs =  UtilsXTool.export_xtool(global_values, objectslist, filename)

    #print(gcode)
    #print(xcs)

    return xcs
