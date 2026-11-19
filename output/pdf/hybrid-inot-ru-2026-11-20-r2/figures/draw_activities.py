"""Emit editable diagrams.net UML activities and matching vector pages. Requires PyMuPDF."""
from pathlib import Path
from xml.etree import ElementTree as ET
import math
import pymupdf as pdf

OUT = Path(__file__).resolve().parent
INK = "#243746"
STROKE = "#536F82"
BLUE = "#EDF4F8"
GREEN = "#EDF5F0"
GOLD = "#FBF2DF"


class Diagram:
    def __init__(self, title, slug, size):
        self.title, self.slug, self.size = title, slug, size
        self.nodes, self.edges, self.guards = {}, [], []

    def node(self, key, kind, box, label="", fill=BLUE):
        self.nodes[key] = (kind, box, label, fill)

    def edge(self, source, source_port, target, target_port, via=()):
        self.edges.append((source, source_port, target, target_port, via))

    def guard(self, label, x, y):
        self.guards.append((label, x, y))

    def point(self, key, port):
        x, y, w, h = self.nodes[key][1]
        a, b = PORTS[port]
        return x + w*a, y+h*b


PORTS = {"t":(.5,0), "b":(.5,1), "l":(0,.5), "r":(1,.5)}
route = Diagram("Dispatch", "uml-route", (394,328))
route.node("start","start",(191,5,12,12))
route.node("setup","action",(69,29,256,32),"Check tool access and set limits")
route.node("prepare","action",(69,74,256,35),"Prepare context and log its cost")
route.node("mode","decision",(112,126,170,55),"Separate sessions\nor parallel work?",GOLD)
route.node("single","action",(6,195,178,40),"Run the introspective cycle\nunder the remaining limits",GREEN)
route.node("multiple","action",(210,195,178,40),"Run the external workflow\nunder the remaining limits",GREEN)
route.node("merge","decision",(190,242,14,14),"",GOLD)
route.node("record","action",(83,268,228,32),"Return candidate, status and run log")
route.node("stop","stop",(190,311,14,14))
route.edge("start","b","setup","t")
route.edge("setup","b","prepare","t")
route.edge("prepare","b","mode","t")
route.edge("mode","l","single","t",[(95,153.5)])
route.edge("mode","r","multiple","t",[(299,153.5)])
route.guard("[No]",82,176)
route.guard("[Yes]",318,176)
route.edge("single","b","merge","l",[(95,249)])
route.edge("multiple","b","merge","r",[(299,249)])
route.edge("merge","b","record","t")
route.edge("record","b","stop","t")

cycle = Diagram("Introspective cycle", "uml-iteration", (430,486))
cycle.node("start","start",(178,4,12,12))
cycle.node("init","action",(86,26,196,31),"Set best = none and best score = -1")
cycle.node("budget","decision",(93,73,182,64),"Attempt, time and\nbudget available?",GOLD)
cycle.node("retrymerge","decision",(354,265,14,14),"",GOLD)
cycle.node("call","action",(85,152,198,34),"Request a plan, K programs\nand their scores")
cycle.node("usage","action",(85,200,198,32),"Count the attempt and log usage")
cycle.node("format","decision",(114,248,140,48),"Valid format?",GOLD)
cycle.node("pick","action",(80,310,208,33),"Select the highest-scored program\nand update the best candidate")
cycle.node("check","action",(80,356,208,33),"Run the external check\nand log verdict, score and message")
cycle.node("pass","decision",(127,404,114,42),"Passed?",GOLD)
cycle.node("diagnostic","action",(299,404,124,42),"Add the test message\nto the next context")
cycle.node("failure","action",(5,317,65,65),"Return best\nor none,\nstatus 0\nand log",GREEN)
cycle.node("success","action",(98,457,172,26),"Return program, status 1 and log",GREEN)
cycle.node("endfail","stop",(30.5,404,14,14))
cycle.edge("start","b","init","t")
cycle.edge("init","b","budget","t")
cycle.edge("budget","l","failure","t",[(37.5,105)])
cycle.guard("[No]",63,97)
cycle.edge("budget","b","call","t")
cycle.guard("[Yes]",204,145)
cycle.edge("call","b","usage","t")
cycle.edge("usage","b","format","t")
cycle.edge("format","r","retrymerge","l")
cycle.edge("retrymerge","t","budget","r",[(361,105)])
cycle.guard("[No]",283,265)
cycle.edge("format","b","pick","t")
cycle.guard("[Yes]",206,303)
cycle.edge("pick","b","check","t")
cycle.edge("check","b","pass","t")
cycle.edge("pass","r","diagnostic","l")
cycle.guard("[No]",267,418)
cycle.edge("diagnostic","t","retrymerge","b")
cycle.edge("pass","b","success","t")
cycle.guard("[Yes]",206,451)
cycle.edge("failure","b","endfail","t")
# Final node under the successful return.
cycle.size=(430,507)
cycle.node("endpass","stop",(177,491,14,14))
cycle.edge("success","b","endpass","t")

context = Diagram("Optional context preparation", "uml-context", (394,318))
context.node("start","start",(191,4,12,12))
context.node("split","action",(81,26,232,32),"Split context into labelled source blocks")
context.node("pin","action",(81,69,232,32),"Keep constraints, target code and interfaces")
context.node("fits","decision",(107,114,180,58),"Do required blocks\nfit the limit?",GOLD)
context.node("rank","action",(208,184,181,39),"Rank optional blocks\nand remove duplicates")
context.node("keep","action",(208,235,181,36),"Keep the highest-ranked blocks\nthat fit the remaining space",GREEN)
context.node("error","action",(5,206,180,42),"Report that required blocks\nexceed the context limit",GREEN)
context.node("okend","stop",(291.5,291,14,14))
context.node("errend","stop",(88,270,14,14))
context.edge("start","b","split","t")
context.edge("split","b","pin","t")
context.edge("pin","b","fits","t")
context.edge("fits","l","error","t",[(95,143)])
context.edge("fits","r","rank","t",[(298.5,143)])
context.guard("[No]",80,175)
context.guard("[Yes]",318,166)
context.edge("rank","b","keep","t")
context.edge("keep","b","okend","t")
context.edge("error","b","errend","t")


def rgb(color):
    return tuple(int(color[i:i+2],16)/255 for i in (1,3,5))


def line(page, points, color=STROKE, width=1.15):
    shape=page.new_shape()
    shape.draw_polyline(points)
    shape.finish(color=rgb(color),width=width,lineJoin=1,closePath=False)
    shape.commit()


def center(page, label, x, y, fs=11, font="helv"):
    lines=label.splitlines()
    for j, row in enumerate(lines):
        length=pdf.get_text_length(row,fontname=font,fontsize=fs)
        baseline=y+(j-(len(lines)-1)/2)*fs*1.12+fs*.32
        page.insert_text((x-length/2,baseline),row,fontname=font,fontsize=fs,color=rgb(INK))


def render(d, parent):
    tab=ET.SubElement(parent,"diagram",id=d.slug,name=d.title)
    graph=ET.SubElement(tab,"mxGraphModel",grid="1",gridSize="10",page="1",pageWidth=str(d.size[0]),pageHeight=str(d.size[1]))
    root=ET.SubElement(graph,"root")
    ET.SubElement(root,"mxCell",id="0")
    ET.SubElement(root,"mxCell",id="1",parent="0")
    doc=pdf.open()
    page=doc.new_page(width=d.size[0],height=d.size[1])
    for i,(a,ap,b,bp,via) in enumerate(d.edges):
        points=[d.point(a,ap),*via,d.point(b,bp)]
        line(page,points)
        x,y=points[-1]
        px,py=points[-2]
        dist=math.hypot(x-px,y-py)
        dx,dy=(x-px)/dist,(y-py)/dist
        triangle=[(x,y),(x-5*dx-2.3*dy,y-5*dy+2.3*dx),(x-5*dx+2.3*dy,y-5*dy-2.3*dx)]
        sh=page.new_shape()
        sh.draw_polyline(triangle+[triangle[0]])
        sh.finish(color=rgb(STROKE),fill=rgb(STROKE),width=.5)
        sh.commit()
        ex,ey=PORTS[ap]
        ix,iy=PORTS[bp]
        style=f"edgeStyle=none;rounded=0;endArrow=block;endFill=1;strokeColor={STROKE};exitX={ex};exitY={ey};entryX={ix};entryY={iy};"
        cell=ET.SubElement(root,"mxCell",id="e"+str(i),parent="1",edge="1",source=a,target=b,style=style)
        geom=ET.SubElement(cell,"mxGeometry",{"relative":"1","as":"geometry"})
        if via:
            arr=ET.SubElement(geom,"Array",{"as":"points"})
            for vx,vy in via:
                ET.SubElement(arr,"mxPoint",x=str(vx),y=str(vy))
    for key,(kind,box,label,fill) in d.nodes.items():
        x,y,w,h=box
        rect=pdf.Rect(x,y,x+w,y+h)
        cx,cy=x+w/2,y+h/2
        style=f"whiteSpace=wrap;html=0;align=center;verticalAlign=middle;fontFamily=Helvetica;fontSize=11;fontColor={INK};fillColor={fill};strokeColor={STROKE};strokeWidth=1.1;"
        if kind=="action":
            page.draw_rect(rect,color=rgb(STROKE),fill=rgb(fill),width=1.1,radius=.16)
            style+="rounded=1;arcSize=18;"
        elif kind=="decision":
            sh=page.new_shape()
            sh.draw_polyline([(cx,y),(x+w,cy),(cx,y+h),(x,cy),(cx,y)])
            sh.finish(color=rgb(STROKE),fill=rgb(fill),width=1.15)
            sh.commit()
            style+="shape=rhombus;"
        else:
            page.draw_circle((cx,cy),w/2-.7,color=rgb(INK),fill=rgb(INK) if kind=="start" else (1,1,1),width=1.2)
            if kind=="stop":
                page.draw_circle((cx,cy),w/2-3.0,color=rgb(INK),fill=rgb(INK),width=.5)
            style+="shape=ellipse;aspect=fixed;"+("fillColor="+INK+";" if kind=="start" else "shape=endState;fillColor="+INK+";")
        if label:
            center(page,label,cx,cy,10.5 if key in ("init","success","diagnostic","failure") else 11)
        cell=ET.SubElement(root,"mxCell",id=key,value=label,style=style,vertex="1",parent="1")
        ET.SubElement(cell,"mxGeometry",{"x":str(x),"y":str(y),"width":str(w),"height":str(h),"as":"geometry"})
    for i,(label,x,y) in enumerate(d.guards):
        center(page,label,x,y,9.2,"hebo")
        cell=ET.SubElement(root,"mxCell",id="g"+str(i),value=label,style="text;html=0;align=center;verticalAlign=middle;fillColor=none;strokeColor=none;fontSize=9;fontStyle=1;",vertex="1",parent="1")
        ET.SubElement(cell,"mxGeometry",{"x":str(x-16),"y":str(y-8),"width":"32","height":"16","as":"geometry"})
    doc.set_metadata({"title":d.title})
    doc.save(OUT/(d.slug+".pdf"),deflate=True)
    doc.close()


if __name__=="__main__":
    mx=ET.Element("mxfile",host="app.diagrams.net",compressed="false")
    for diagram in (route,cycle,context):
        render(diagram,mx)
    ET.indent(mx)
    ET.ElementTree(mx).write(OUT/"hybrid-activities.drawio",encoding="utf-8",xml_declaration=True)
