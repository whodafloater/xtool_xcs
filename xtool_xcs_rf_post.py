#
#
#  CAM post processor to generate XTool Creative Space project file

#  leveraged from FreeCad/src/Mod/CAM/Path/Post/scripts/generic_post.py


import os
from Path.Post.Processor import PostProcessor
import Path
import FreeCAD

Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

translate = FreeCAD.Qt.translate

debug = True
if debug:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


class Xtool_xcs_rf(PostProcessor):
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
        return 'export out'

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

