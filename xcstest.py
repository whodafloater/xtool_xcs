
import xtool_xcs as xt
import json

def main():
    line1 = xt.XcsLine('line1', xt.XcsPnt(1,2), xt.XcsPnt(3,4))
    rect1 = xt.XcsRect('rect1', xt.XcsPnt(10,12), xt.XcsPnt(20,22))
    circ1 = xt.XcsCircle('circ1', xt.XcsPnt(50,20), xt.XcsPnt(60,30))

    penpoints = list()
    penpoints.append (xt.point(100,100))
    penpoints.append (xt.point(105,100))
    penpoints.append (xt.point(105,110))
    pentri = xt.XcsPen('pen1').setpoints(penpoints)
    #pentri.add_process('VECTOR_CUTTING', 81, 31, 2)

    pentri.place(200,200).size(45,55).add_process('VECTOR_CUTTING', 81, 31, 2)

    # the 4 point star from the shape menu
    star_svg = "m19 18.5-.5.5-16.3 7.2 16.3 7.2c.2 0 .4.3.5.5l7.2 16.3 7.2-16.3c0-.2.3-.4.5-.5l16.3-7.2L33.9 19a1 1 0 0 1-.5-.5L26.2 2.2 19 18.5Z"
    star = xt.XcsPath('path1').setpath(100, 50, star_svg)
    star2 = xt.XcsPath('path2').setpath(100, 50, star_svg)

 
    ell = xt.XcsPath('elly').setpath(1, 1,
        "M24.5 25.8c-.7 0-1.3-.6-1.3-1.3V1.8A1.3 1.3 0 0 0 22 .5H1.8A1.3 1.3 0 0 0 .5 1.8v45.4c0 .7.6 1.3 1.3 1.3h45.4a1.3 1.3 0 0 0 1.3-1.3V27a1.3 1.3 0 0 0-1.3-1.2H24.5Z"
       )

    ctest = xt.XcsPath('ctest').setpath(20, 50,
        "M100 100 c   -3  -20  13 7   10 10 v 20 h -5 Z"
       )

    canvas1 = xt.XcsCanvas();
    canvas1.add_element(rect1);
    canvas1.add_element(circ1);
    canvas1.add_element(pentri);
    canvas1.add_element(ctest);
    canvas1.add_element(xt.XcsText('t1', 'sometext').place(300,50).size(0,10).add_process('VECTOR_ENGRAVING', 50, 80, 1));

    canvas2 = xt.XcsCanvas();
    canvas2.add_element(line1);

    xt.XcsProcess(ell, 'VECTOR_CUTTING', 15, 25, 1)

    canvas3 = xt.XcsCanvas();
    canvas3.add_element(ell);
    #canvas3.title = "tom"

    rect1.group('gp1')
    circ1.group('gp1')

    xt.XcsProcess(rect1, 'VECTOR_CUTTING', 81, 31, 2)
    xt.XcsProcess(circ1, 'VECTOR_CUTTING', 55, 21, 2)
    xt.XcsProcess(line1, 'VECTOR_CUTTING', 31, 80, 1)

    canvas2.add_element(star);
    star.add_process('VECTOR_CUTTING', 15, 25, 1)
    canvas2.add_element(star2);
    star2.place(110,55)

    xt.XcsCanvas.active_canvas = canvas1

    xcs = xt.XcsCanvas.canvi_encode() 
    xcs = xcs | dict(version = "1.1.19", extId = "D1")
    xcs = xcs | xt.XcsCanvas.device_encode()

    outfile = open('xcstest.xcs', mode='w')
    json.dump(xcs, outfile, cls=xt.XcsEncode)

    outfile = open('xcstest.xcs.txt', mode='w')
    json.dump(xcs, outfile, cls=xt.XcsEncode, indent=3)

if __name__ == '__main__':
    main()

