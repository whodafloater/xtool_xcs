# xtool_xcs



## Features

-A python module for generating .xcs project files for xTool Creative Space



-A FreeCAD Path post processor to generate a .xcs project file directly
from FreeCAD's Tool Path module

## xTool Creative Space versions

Works with version v1.1.24

Version v1.5.10, shapes work, processing breaks

Version v2, more stuff breaks

## Installation

Just copy some files into you FreeCAD macro directory.

See the Makefile. It works on a windows installation using Msys2
for a shell. Adjust the paths for you system.


```sh
make install
```

## Usage

test_cuts.py is an example program that generates an array of cuts with various parameters.

```sh
python test_cuts.py
```

For the freeCAD path processor: See  FreeCAD DOC [fcpathworkbench]

Use the job template file when creating a new job:

```
 job_xtoolD1_3mm_wood.json
```

Edit this file or export a new one from the Job Editor.
The tools tab in the Job Editor is where you set speed and power for
each of you "tools". The "Export" button is hidden at the bottom of the "General" tab.


For multi pass cutting operations use the tool step down parameter.
If your model is 3mm thick, setting the step down to 1.5mm will give you
two passes. The path objects in the resulting xcs file will have two passes.
The "Pass" field in xTool should be set to 1.

FreeCAD funny's
- if you select the top surface of your part and do a profile operation 
you'll get a single pass cut

- if you select the bottom surface of your part you get a full 2.5D cutting
operation and the step down param will determine how many passes you get.
You can also selct whether or not to process holes and cutouts.



## License

MIT

[//]:#
[fcpathworkbench]: <https://wiki.freecad.org/Path_Workbench>
[fcprefs]: <https://wiki.freecad.org/Path_Preferences>
