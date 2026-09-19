import fontforge

LIGS = ["period_period_period","exclam_equal_equal","exclam_equal",
"star_star_star_star","asterisk_asterisk_asterisk","asterisk_slash","asterisk_asterisk",
"slash_greater","slash_asterisk",
"hyphen_hyphen_greater","hyphen_hyphen_hyphen","hyphen_hyphen","hyphen_greater",
"underscore_underscore","ampersand_ampersand","plus_plus",
"equal_equal_equal","equal_equal","equal_greater",
"greater_greater","greater_equal",
"less_exclam_hyphen_hyphen","less_hypen","less_slash","less_less","less_equal"]

src = fontforge.open("research/DepartureMonoLigatures-Regular.otf")
dst = fontforge.open("build/DepartureMono-Viet.otf")

missing = []
copied = 0
for name in LIGS:
    if name not in src:
        missing.append(name)
        continue
    src.selection.select(name)
    src.copy()
    if name not in dst:
        dst.createChar(-1, name)
    dst.selection.select(name)
    dst.paste()
    dst[name].width = src[name].width
    copied += 1

print(f"Copied {copied}/{len(LIGS)}; missing from source: {missing}")
dst.save("build/DepartureMono-Viet.sfd")
dst.generate("build/DepartureMono-Viet.otf")
