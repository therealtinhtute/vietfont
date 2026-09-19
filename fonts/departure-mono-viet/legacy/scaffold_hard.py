import fontforge, unicodedata

f = fontforge.open("build/DepartureMono-Viet.otf")

full_lower = "aăâeêoôơuưy"
targets_lower = "aáàảãạăắằẳẵặâấầẩẫậeéèẻẽẹêếềểễệiíìỉĩịoóòỏõọôốồổỗộơớờởỡợuúùủũụưứừửữựyýỳỷỹỵ"
full = targets_lower + targets_lower.upper()

modifier_name = {0x0306:"breve", 0x0302:"circumflex", 0x031B:"horn"}

rows = []
for ch in full:
    nfd = unicodedata.normalize("NFD", ch)
    if len(nfd) != 3:
        continue  # only 2-mark (base+modifier+tone) composites
    base, m1, m2 = nfd[0], ord(nfd[1]), ord(nfd[2])
    mods = [m1, m2]
    modifier_cp = next(c for c in mods if c in modifier_name)
    tone_cp = next(c for c in mods if c not in modifier_name)
    is_upper = base.isupper()
    base_lower = base.lower()
    mod_glyph = base_lower + modifier_name[modifier_cp]
    if is_upper:
        mod_glyph = mod_glyph[0].upper() + mod_glyph[1:]
    rows.append((ch, ord(ch), mod_glyph, hex(tone_cp)))

print(f"{len(rows)} hard-group glyphs to scaffold")
count = 0
for ch, cp, mod_glyph, tone_hex in rows:
    if mod_glyph not in f:
        print(f"  MISSING SOURCE {mod_glyph} for {ch} (U+{cp:04X})")
        continue
    name = f"uni{cp:04X}"
    if name not in f:
        f.createChar(cp, name)
    g = f[name]
    g.clear()
    src = f[mod_glyph]
    pen = g.glyphPen()
    for c in src.foreground:
        pts = [(p.x,p.y) for p in c]
        pen.moveTo(*pts[0])
        for p in pts[1:]:
            pen.lineTo(*p)
        pen.closePath()
    pen = None
    g.width = 350
    g.color = 0xFF8800  # orange = TODO marker, visible in FontForge glyph grid
    g.comment = f"TODO: add tone mark U+{tone_hex[2:].upper()} on top of {mod_glyph}"
    count += 1

print(f"Scaffolded {count} glyphs (orange = needs hand-drawn tone mark)")
f.save("build/DepartureMono-Viet.sfd")
f.generate("build/DepartureMono-Viet.otf")
