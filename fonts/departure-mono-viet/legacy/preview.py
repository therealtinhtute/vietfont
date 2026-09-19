import fontforge, sys

PX = 50  # units per pixel
TOP_Y = 550   # ascent, row 0
ROWS = 14
COLS = 7

def rects_to_grid(rects):
    grid = [[False]*COLS for _ in range(ROWS)]
    for (x0,y0,x1,y1) in rects:
        c0, c1 = int(x0//PX), int(x1//PX)
        r0, r1 = int((TOP_Y - y1)//PX), int((TOP_Y - y0)//PX)
        for r in range(max(0,r0), min(ROWS,r1)):
            for c in range(max(0,c0), min(COLS,c1)):
                grid[r][c] = True
    return grid

def grid_to_block_lines(grid):
    lines = []
    for pair in range(ROWS//2):
        top = grid[pair*2]
        bot = grid[pair*2+1]
        line = ''
        for x in range(COLS):
            t,b = top[x], bot[x]
            line += '█' if t and b else ('▀' if t else ('▄' if b else ' '))
        lines.append(line)
    return lines

def glyph_rects(f, name):
    g = f[name]
    return [c.boundingBox() for c in g.foreground]

def print_glyph(name, rects):
    print(f"[{name}]")
    for l in grid_to_block_lines(rects_to_grid(rects)):
        print('|'+l+'|')
    print()

if __name__ == "__main__":
    f = fontforge.open("font-src/DepartureMono-Regular.otf")
    for name in sys.argv[1:]:
        print_glyph(name, glyph_rects(f, name))

def print_composite(name, base_glyph, extra_rects, f=None):
    if f is None:
        f = fontforge.open("font-src/DepartureMono-Regular.otf")
    rects = glyph_rects(f, base_glyph) + extra_rects
    print_glyph(name, rects)
