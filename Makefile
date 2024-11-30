
OS = $(shell uname -o)

ifeq ($(OS), Msys)
    programs = /c/users/$(USER)/AppData/Local/Programs
    freecad = FreeCAD\ 0.21
    modpath = Mod/Path/

    fc_mod_path_post_dir = $(programs)/$(freecad)/$(modpath)/PathScripts/post
    fc_macro_dir = /c/users/$(USER)/AppData/Roaming/FreeCAD/Macro
else
    fc_mod_path_post_dir = /tmp
    fc_macro_dir = /tmp
    $(error echo $(OS) not supported in Makefile)
endif

all: hello_world.xcs xcstest.xcs test_cuts.pretty README.html

# Make sure paths are right.
# These file should be present from the FreeCAD install
# FreeCAD 0.20
#install: | $(fc_mod_path_post_dir)/linuxcnc_post.py
#install: | $(fc_macro_dir)/Bit/5mm_Drill.fctb


# FreeCAD 0.21
install: | $(fc_macro_dir)/Bit/5mm_Drill.fctb

install: xtool_xcs.py xtool_xcs_post.py 
	#rm -f $(fc_mod_path_post_dir)/xtool_xcs.py
	#rm -f $(fc_mod_path_post_dir)/xtool_xcs_post.py
	mkdir -p $(fc_mod_path_post_dir)
	cp xtool_xcs.py      $(fc_macro_dir)/xtool_xcs.py
	cp xtool_xcs_post.py $(fc_macro_dir)/xtool_xcs_post.py
	cp laser_tools.fctl  $(fc_macro_dir)/Library/laser_tools.fctl
	cp 300um_laser.fctb  $(fc_macro_dir)/Bit/300um_laser.fctb
	cp 200um_laser.fctb  $(fc_macro_dir)/Bit/200um_laser.fctb
	cp job_xtoolD1_3mm_wood.json $(fc_macro_dir)/job_xtoolD1_3mm_wood.json

hello_world.xcs:  xtool_xcs.py
	python xtool_xcs.py

xcstest.xcs : xcstest.py xtool_xcs.py
	python xcstest.py

test_cuts.xcs : test_cuts.py xtool_xcs.py
	python test_cuts.py

test_cuts.pretty : test_cuts.xcs
	python -m json.tool test_cuts.xcs > $@

README.html : README.md
	markdown $^ > $@

clean:
	rm -f *.xcs *.xcs.txt *.pretty
