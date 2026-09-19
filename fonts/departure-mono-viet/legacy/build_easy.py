import fontforge

f = fontforge.open("font-src/DepartureMono-Regular.otf")

def set_glyph(name, cp, rects):
    if name not in f:
        f.createChar(cp, name)
    g = f[name]
    g.clear()
    pen = g.glyphPen()
    for (x0,y0,x1,y1) in rects:
        pen.moveTo(x0,y0); pen.lineTo(x1,y0); pen.lineTo(x1,y1); pen.lineTo(x0,y1); pen.closePath()
    pen = None
    g.width = 350

def rects_of(name):
    return [c.boundingBox() for c in f[name].foreground]

# 1. ohorn / Ohorn
set_glyph("ohorn", 0x01A1, rects_of("o") + [(250,300,300,350)])
set_glyph("Ohorn", 0x01A0, rects_of("O") + [(300,350,350,450)])

# 2. hookabovecomb (lowercase-band standalone mark)
hook_lower = [(200,400,250,450),(100,350,150,400),(150,350,200,400)]
set_glyph("hookabovecomb", 0x0309, hook_lower)
hook_upper = [(x0,y0+100,x1,y1+100) for (x0,y0,x1,y1) in hook_lower]

# 3. hookabove composites on plain vowels
lower_map = {"a":0x1EA3, "e":0x1EBB, "i":0x1EC9, "o":0x1ECF, "u":0x1EE7, "y":0x1EF7}
upper_map = {"A":0x1EA2, "E":0x1EBA, "I":0x1EC8, "O":0x1ECE, "U":0x1EE6, "Y":0x1EF6}
for base, cp in lower_map.items():
    set_glyph(f"uni{cp:04X}", cp, rects_of(base) + hook_lower)
for base, cp in upper_map.items():
    set_glyph(f"uni{cp:04X}", cp, rects_of(base) + hook_upper)

# 4. dotbelow on y/Y
dot = rects_of("dotbelowcomb")
set_glyph("uni1EF5", 0x1EF5, rects_of("y") + dot)
set_glyph("uni1EF4", 0x1EF4, rects_of("Y") + dot)

f.save("build/DepartureMono-Viet.sfd")
f.generate("build/DepartureMono-Viet.otf")
print("Done. Saved .sfd and .otf")
