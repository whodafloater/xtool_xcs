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
            addtestbox(canvas2, w, h, x, y, p, s, npass)

    xt.XcsCanvas.active_canvas = canvas1
    xt.XcsSave('test_cuts')

if __name__ == '__main__':
    main()
