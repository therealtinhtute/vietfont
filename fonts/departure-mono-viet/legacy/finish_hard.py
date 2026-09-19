import fontforge, unicodedata

f = fontforge.open("build/DepartureMono-Viet.sfd")

full_lower = "aăâeêoôơuưy"
targets_lower = "aáàảãạăắằẳẵặâấầẩẫậeéèẻẽẹêếềểễệiíìỉĩịoóòỏõọôốồổỗộơớờởỡợuúùủũụưứừửữựyýỳỷỹỵ"
full = targets_lower + targets_lower.upper()

modifier_name = {0x0306: "breve", 0x0302: "circumflex", 0x031B: "horn"}
tone_mark_glyph = {0x0300: "gravecomb", 0x0301: "acutecomb", 0x0303: "tildecomb",
                    0x0309: "hookabovecomb", 0x0323: "dotbelowcomb"}

def rects_of(name):
    return [c.boundingBox() for c in f[name].foreground]

def set_glyph(name, rects, width=350):
    if name not in f:
        f.createChar(-1, name)
    g = f[name]
    g.clear()
    pen = g.glyphPen()
    for (x0, y0, x1, y1) in rects:
        pen.moveTo(x0, y0); pen.lineTo(x1, y0); pen.lineTo(x1, y1); pen.lineTo(x0, y1); pen.closePath()
    pen = None
    g.width = width
    g.color = -1
    g.comment = ""

rows = []
for ch in full:
    nfd = unicodedata.normalize("NFD", ch)
    if len(nfd) != 3:
        continue
    base, m1, m2 = nfd[0], ord(nfd[1]), ord(nfd[2])
    mods = [m1, m2]
    modifier_cp = next(c for c in mods if c in modifier_name)
    tone_cp = next(c for c in mods if c not in modifier_name)
    is_upper = base.isupper()
    base_lower = base.lower()
    mod_glyph = base_lower + modifier_name[modifier_cp]
    if is_upper:
        mod_glyph = mod_glyph[0].upper() + mod_glyph[1:]
    rows.append((ch, ord(ch), mod_glyph, tone_cp, is_upper))

print(f"{len(rows)} hard-group glyphs to finish")
count = 0
for ch, cp, mod_glyph, tone_cp, is_upper in rows:
    name = f"uni{cp:04X}"
    if mod_glyph not in f:
        print(f"  MISSING SOURCE {mod_glyph} for {ch} (U+{cp:04X})")
        continue

    base_rects = rects_of(mod_glyph)
    tone_glyph = tone_mark_glyph[tone_cp]
    tone_rects = rects_of(tone_glyph)

    if tone_cp == 0x0323:
        shift = 0
    elif is_upper:
        shift = 0
    else:
        shift = 100

    shifted_tone = [(x0, y0 + shift, x1, y1 + shift) for (x0, y0, x1, y1) in tone_rects]
    set_glyph(name, base_rects + shifted_tone)
    count += 1

print(f"Finished {count} glyphs")
f.save("build/DepartureMono-Viet.sfd")
f.generate("build/DepartureMono-Viet.otf")
print("Saved .sfd and .otf")
