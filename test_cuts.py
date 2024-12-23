#!python3

import xtool_xcs as xt
import json

def steps(start, stop, n):
    d = list()
    for i in range(n):
        d.append(start + (stop-start) * (i) / (n-1))
    return d

def annotation(text, x, y):
    return xt.XcsText('', text) .place(x,y) .size(0,3) .origin(5) .add_process('VECTOR_ENGRAVING', 50, 80, 1)

def addtestbox(canvas, w, h, x, y, p, s, n):
    r = xt.XcsRect('rect', xt.XcsPnt(0,0), xt.XcsPnt(10,10))
    r. place(x, y). size(w, h) .add_process('VECTOR_CUTTING', p, s, n)
    canvas.add_element(r)
    canvas.add_element(annotation(str(int(p)), x+w/2, y+h*1/4))
    canvas.add_element(annotation(str(int(s)), x+w/2, y+h*2/4))
    canvas.add_element(annotation(str(int(n)), x+w/2, y+h*3/4))
    return r

def addtestU(canvas, w, h, x, y, p, s, n):
    # cut a U shape so it does not fall apart

    points = [xt.XcsPnt(x, y),
              xt.XcsPnt(x, y + h),
              xt.XcsPnt(x + w, y + h),
              xt.XcsPnt(x + w, y),
             ]

    path = xt.XcsPen('U').setpoints(points).add_process('VECTOR_CUTTING', p, s, n)
    path.width = w
    path.height = h

    canvas.add_element(path)
    canvas.add_element(annotation(str(int(p)), x+w/2, y+h*1/4))
    canvas.add_element(annotation(str(int(s)), x+w/2, y+h*2/4))
    canvas.add_element(annotation(str(int(n)), x+w/2, y+h*3/4))

def main():

    w = 10
    h = 20

    n = 6
    m = 3

    npass = 1
    speed = steps(80, 10,  n)
    power = steps(50, 100, m)

    canvas1 = xt.XcsCanvas()

    for pi in range(m):
        for si in range(n):
            x = si*(w+5)
            y = pi*(h+5)
            s = speed[si]
            p = power[pi]
            addtestbox(canvas1, w, h, x, y, p, s, npass)

    n = 6
    m = 3
    npass = 2
    speed = steps(5,   10, n)
    power = steps(70, 100, m)

    canvas2 = xt.XcsCanvas()
    for pi in range(m):
        for si in range(n):
            x = si*(w+5)
            y = pi*(h+5)
            s = speed[si]
            p = power[pi]
            #addtestbox(canvas2, w, h, x, y, p, s, npass)
            addtestU(canvas2, w, h, x, y, p, s, npass)


    # 3mm corrugated cardboard
    n = 3
    m = 3
    npass = 1
    speed = steps(30,  10, n)
    power = steps(70, 100, m)

    canvas3 = xt.XcsCanvas()
    for pi in range(m):
        for si in range(n):
            x = 5 + si*(w+5)
            y = 5 + pi*(h+5)
            s = speed[si]
            p = power[pi]
            addtestU(canvas3, w, h, x, y, p, s, npass)

    # surrounding box at last speed and power setting
    # to cut this test card from the panel
    r = xt.XcsRect('rect', xt.XcsPnt(0,0), xt.XcsPnt(10,10))
    r. place(0, 0). size(5+(w+5)*n, 5+(h+5)*m) .add_process('VECTOR_CUTTING', p, s, npass)
    canvas3.add_element(r)



    # 4mm foam core
    # none of these worked. foam just melts between paper and reflows.
    # if you get it hot enough backsdie paper will burn but not cut.
    # yes, using air.
    n = 3
    m = 3
    npass = 4
    speed = steps(15, 5,  n)
    power = steps(30, 60, m)

    canvas4 = xt.XcsCanvas()
    for pi in range(m):
        for si in range(n):
            x = 5 + si*(w+5)
            y = 5 + pi*(h+5)
            s = speed[si]
            p = power[pi]
            addtestU(canvas4, w, h, x, y, p, s, npass)

    # surrounding box at last speed and power setting
    # to cut this test card from the panel
    r = xt.XcsRect('rect', xt.XcsPnt(0,0), xt.XcsPnt(10,10))
    r. place(0, 0). size(5+(w+5)*n, 5+(h+5)*m) .add_process('VECTOR_CUTTING', p, s, npass)
    canvas4.add_element(r)




    xt.XcsCanvas.active_canvas = canvas1
    xt.XcsSave('test_cuts')

if __name__ == '__main__':
    main()
