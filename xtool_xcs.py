
import json
import os

class XcsPnt:
    x = 0;
    y = 0;
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def encode(self):
        return {'x':self.x, 'y':self.y}

class Xcs2dAttr:
    name = 'none'
    p = XcsPnt(0, 0)
    def __init__(self, name, x, y):
        self.name = name
        self.p = XcsPnt(x, y)
    def encode(self):
        return {self.name: self.p.encode}

# scale values are the result of a GUI width and height change
#    we cannot drive these
# offset values are the result of a GUI position change
#    we cannot drive these
#
# x, y, width, height and height determine size and placement
# x, y positions the upper left corner of the objects bounding box
class XcsPrim:
    type = 'none'

    def __init__(self):
        self.id = "none"
        self.x = 0;
        self.y = 0;
        self.angle = 0;
        self.scale =     Xcs2dAttr('scale', 1, 1)
        self.skew =      Xcs2dAttr('skew', 0, 0)
        self.pivot =     Xcs2dAttr('pivot', 0, 0)
        self.localSkew = Xcs2dAttr('localSkew', 0, 0)
        self.offsetX = 0
        self.offsetY = 0
        self.lockRatio = True
        self.isClosePath = True
        self.zOrder = 0
        self.width = 10
        self.height = 10
        self.isFill = False
        self.lineColor = 0x551100
        self.fillColor = 0x777777
        self.groupTag = ""

    def add_process(self, proc_type, power, speed, repeat):
        XcsProcess(self, proc_type, power, speed, repeat)
        return self

    def place(self, x, y):
        self.x = x
        self.y = y
        return self

    def size(self, w, h):
        self.width = w
        self.height = h
        return self

    def group(self, gid):
        self.groupTag = gid
        return self

    def encode(self):
        d = dict(id = self.id,
                   type = self.type,
                   x = self.x,
                   y = self.y,
                   angle = self.angle,
                   scale = self.scale.p.encode(),
                   skew = self.skew.p.encode(),
                   pivot = self.pivot.p.encode(),
                   localSkew = self.localSkew.p.encode(),
                   offsetX = self.offsetX,
                   offsetY = self.offsetY,
                   lockRatio = self.lockRatio,
                   isClosePath = self.isClosePath,
                   zOrder = self.zOrder,
                   width = self.width,
                   height = self.height,
                   isFill = self.isFill,
                   lineColor = self.lineColor,
                   fillColor = self.fillColor,
                  )
        if self.groupTag != "":
            d['groupTag'] = self.groupTag
        return d

class XcsRect(XcsPrim):
    type = 'RECT'
    def __init__(self, id, p1, p2):
        XcsPrim.__init__(self)
        self.id = id
        self.x = p1.x
        self.y = p1.y
        self.width = abs(p2.x - p1.x)
        self.height = abs(p2.y - p1.y)

class XcsLine(XcsPrim):
    type = 'LINE'
    p2 = Xcs2dAttr('endPoint',12,12)
    def __init__(self, id, p1, p2):
        XcsPrim.__init__(self)
        self.id = id
        self.x = p1.x
        self.y = p1.y
        self.p2 = Xcs2dAttr('endPoint', p2.x, p2.y)

    def encode(self):
        x = XcsPrim.encode(self)
        x[self.p2.name] = self.p2.p
        return x
        # 3.9 feature
        #return XcsPrim.encode(self) | {self.p2.name : self.p2.p}

class XcsCircle(XcsPrim):
    type = 'CIRCLE'
    def __init__(self, id, p1, p2):
        XcsPrim.__init__(self)
        self.id = id
        self.x = p1.x
        self.y = p1.y
        self.width = abs(p2.x - p1.x)
        self.height = abs(p2.y - p1.y)

class XcsPen(XcsPrim):
    type = 'PEN'
    def __init__(self, id):
        XcsPrim.__init__(self)
        self.id = id
        self.points = list()
        self.controlPoints = dict()
        self.isClosePath = False

    def setpoints(self, a):
        self.points = a
        self.x = (a[0]).x
        self.y = (a[0]).y
        return self

    def encode(self):
        x = XcsPrim.encode(self)
        x['points'] = self.points
        x['controlPoints'] = self.controlPoints
        return x
        # 3.9 feature
        #return XcsPrim.encode(self) | {'points':self.points, 'controlPoints':self.controlPoints} 

# graphicX, graphicY don't drive size or placement. GUI side effects
class XcsPath(XcsPrim):
    type = 'PATH'
    dPath = ''
    graphicX = 0
    graphicY = 0
    def __init__(self, id):
        XcsPrim.__init__(self)
        self.id = id
        self.points = list()
        self.dPath = ''
        self.graphicX = 0
        self.graphicy = 0

    def setpoints(self, a):
        self.points = a
        self.x = (a[0]).x
        self.y = (a[0]).y
        return self

    def setpath(self, x, y, path):
        self.dPath = path
        self.x = x
        self.y = y
        return self

    def encode(self):
        d = XcsPrim.encode(self)
        d['points'] = self.points
        d['dPath'] = self.dPath
        d['graphicX'] = self.graphicX
        d['graphicY'] = self.graphicY
        return d

class XcsText(XcsPrim):
    type = 'TEXT'

    def __init__(self, id, text):
        XcsPrim.__init__(self)
        self.id = id
        self.text = text
        self.resolution = 1
        self.aspect = 0.6
        self.ox = 0 
        self.oy = 0
        self.org = 1

        # good for numbers
        #  "fontFamily": "SWGDT",
        #  "fontSource": "system",
        #
        #  old versions of xcs would give priority to width
        #  and fit the font to the box. No so with version v2.2.23
        #  size 12 is about 2.1mm width
        #  
        #  So, hack for V2 is to compute fontsize based on width of
        #  the text box and how many chars are in it.
        self.fontScale = 12 / 2.1
        #
        self.style = {
                       "fontFamily": "Lato",
                       "fontSource": "build-in",
                       "fontSize": 72,
                       "fontSubfamily": "Regular",
                       "letterSpacing": 0,
                       "leading": 0,
                       "align": "left"
                     }

    # where to place origin of text box.
    # final x,y is upper left corner of bounding box.
    def place(self, x, y):
        self.ox = x 
        self.oy = y
        return self

    # set character size
    def size(self, w, h):
        if w == 0:
           self.w = h * self.aspect
        else:
           self.aspect = w/h
        self.height = h
        return self

    # text origin map:
    #      1  2  3
    #      4  5  6
    #      7  8  9
    def origin(self, org):
        self.org = org
        return self

    def encode(self):
        self.width = self.aspect * len(self.text) * self.height
        #if self.text == '1':
        #    self.width = self.aspect * self.height * 0.5
        self.x = self.ox - self.width  * ((self.org-1)%3)/2
        self.y = self.oy - self.height * int((self.org-1)/3)/2
        self.style["fontSize"] = self.fontScale * self.width / float(len(self.text))
        d = XcsPrim.encode(self)
        d['text'] = self.text
        d['resolution'] = self.resolution
        d['style'] = self.style
        return d

class XcsHeadParam():
    name = 'customize'
    power = 0
    speed = 10
    repeat = 1
    def __init(self, name, power, speed, repeat):
        self.name = name
        self.power = power
        self.speed = speed
        self.repeat = repeat


class XcsProcess():
    primitive = XcsPrim
    selected = 'VECTOR_CUTTING'
    options = dict()
    params = dict()
    pathtype = 'PATH'
    isFill = False

    def __init__(self, primitive, proc_type, power, speed, repeat):
        self.primitive = primitive
        primitive.process = self
        self.selected = proc_type

        self.params = dict()
        self.params[proc_type] = dict(materialType = 'customize',
                                      processIgnore = False,
                                     )
        self.params[proc_type]['parameter'] = dict()
        self.params[proc_type]['parameter']['customize'] = dict(power = power, speed = speed, repeat = repeat)

    def encode(self):
       return dict(processingType = self.selected, data = self.params, type = self.primitive.type, isFill = self.primitive.isFill)


class XcsCanvas():
    canvi = list()

    def __init__(self):
        XcsCanvas.canvi.append(self)
        numcanvi = len(XcsCanvas.canvi)
        self.id = 'canvas' + str(numcanvi)
        self.ids = list()
        self.nid = 0
        self.title = '{panel}' + str(numcanvi)
        self.elements = list()
        XcsCanvas.active_canvas = self

    def add_element(self, e):
        self.elements.append(e)
        self.nid += 1
        if e.id == "":
            e.id = e.type
        if e.id in self.ids:
            while e.id + "__" + str(self.nid) in self.ids:
                self.nid += 1;
            e.id =  e.id + "__" + str(self.nid)
        self.ids.append(e.id)
        XcsCanvas.active_canvas = self
        return self

    def canvi_encode():
        return dict(canvasId = XcsCanvas.active_canvas.id, canvas = XcsCanvas.canvi)

    def encode(self):
        return dict(id = self.id, title = self.title, displays = self.elements)

    def device_encode():
        canvas_ops = list()
        null = 0

        for c in XcsCanvas.canvi:
            laser_plane = dict(material = 0, thickness = null, diameter = null, perimeter = null)
            mode = dict(material = 1, thickness = 3, LASER_PLANE = laser_plane)

            procmap = list()
            for e in c.elements:
                if hasattr(e, 'process'):
                    procmap.append(list((e.id, e.process)))

            displays = dict(dataType = 'Map', value = procmap)

            canvas_op = dict(mode = "LASER_PLANE", data = mode, displays = displays)

            canvas_ops.append((c.id, canvas_op))

        device = dict()
        device['id'] = 'MD1'
        device['power'] = 10
        device['data'] = dict(dataType = 'Map', value = canvas_ops)
        device['materialList'] = []
        return dict(device = device)


class XcsEncode(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, XcsCanvas):
            return obj.encode()
        if isinstance(obj, XcsPnt):
            return obj.encode()
        if isinstance(obj, XcsPrim):
            return obj.encode()
        if isinstance(obj, XcsProcess):
            return obj.encode()
        return json.JSONEncoder.default(self, obj)

def XcsSave(filename):
    xcs = XcsCanvas.canvi_encode() 

    # 3.9
    #xcs = xcs | dict(version = "1.1.19", extId = "D1")
    #xcs = xcs | XcsCanvas.device_encode()

    # for 3.6
    xcs['version'] = '1.1.19'
    xcs['extID'] = 'D1'
    xcs['device'] = XcsCanvas.device_encode()['device']

    print(f'XcsSave filename = {filename}')

    if filename == '-':
       return json.dumps(xcs, cls=XcsEncode)
    else:
       outfile = open(filename + '.xcs', mode='w')
       json.dump(xcs, outfile, cls=XcsEncode)
       return


def point(x,y):
    return dict(x = x, y = y)

def main():

    rect = XcsRect('rect', XcsPnt(0,0), XcsPnt(10,10))

    canvas = XcsCanvas();
    canvas.add_element(rect);

    rect.place(20, 20).size(80, 30).add_process('VECTOR_CUTTING', 100, 6, 2)

    canvas.add_element(XcsText('', 'Hello World!')
        .place(60,35)
        .size(0,10)
        .origin(5)
        .add_process('VECTOR_ENGRAVING', 50, 80, 1));

    XcsSave('hello_world')

if __name__ == '__main__':
    main()

