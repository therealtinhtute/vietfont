# Repository Guidelines

## Project Overview

`vietfont` is a Python CLI that adds Vietnamese diacritic glyphs to pixel/bitmap fonts. It reads a
source font, works out which of the 134 precomposed Vietnamese NFC characters are missing, composes
them from base letters + marks, writes them back with fontforge, and verifies the result with
deterministic checks.

The concrete result shipped in this repo is **Departure Mono Viet**: 134/134 Vietnamese characters,
with all 134 target glyphs passing base-shape preservation — each base contour is either present
identically in the output, or its rasterized pixel footprint is fully covered (the `i`-dot case).

The governing design principle, and the thing most likely to be violated by a well-meaning change:

> **Code owns the pipeline and every blocking check. The Jev model is an advisory signal only.**

Jev (TypeSafe System One) was measured at **62%** accuracy across all Vietnamese glyphs (80% on a
60-glyph lowercase sample). It is never a gate. See `docs/research/jev-verification-limits.md`.

## Architecture & Data Flow

```
analyze → extract → plan → compose → build → verify → proof
                                              │         │
                                              │         └─ human review (final)
                                              └─ deterministic gate (blocking)

judge — off-path advisory branch: ranks glyphs for a human, never blocks
```

```
fontforge font ──> analyze() ──> Analysis(missing, missing_carriers, missing_marks, Grid)
                                      │
marks.json ───────────────────────────┤
                                      ▼
                        compose(font, char, pack, grid) ──> Composition
                          ├── _carrier()      base glyph, or pack modifier
                          ├── _tone()         font mark, or pack mark
                          ├── ensure_winding() align mark winding to carrier
                          ├── _tone_shift()   lift mark above the obstacle
                          ├── _fits()         fall back to compact_mark
                          ├── _dedupe()       absorb carrier dots inside marks
                          └── _shares_rows()  fall back to compact modifier
                                      │
                                      ▼
                        extend() ──> add_glyph() [fontforge] ──> save() ──> .otf
                                      │
                                      ▼
                        rename() [fontTools] — patches nameIDs 1,2,3,4,6,16,17 (+0 if a note is given)
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
        verify() [gate]         proof() [HTML]          judge() [advisory]
```

**fontforge vs fontTools split.** `fontforge` does all vector work: reading `glyph.foreground`,
drawing via `glyph.glyphPen()`, creating chars, editing metrics, generating the font. `fontTools` is
used in exactly one place — `build.py:rename()` — because `fontforge.generate()` writes nameID 1 but
omits nameID 16 (typographic family), which makes macOS conflate the derivative with the original.

**Grid model.** `Grid(pitch, cols, rows, top)` is frozen. `Grid.detect()` reads `os2_typoascent` as
`top`, takes the advance width from `a`/`o`/`O`, then finds the largest divisor of that advance
accounting for ≥95% of all contour coordinates (`_COVERAGE = 0.95`). Departure Mono resolves to
7 cols × 14 rows, pitch 50, top 550 (15 rows at `--ascent 600`).

**Contour model.** A `Contour` is `list[tuple[float, float]]` — a closed polygon. Contours are read
vertex-for-vertex from `glyph.foreground` and **never** reduced to bounding boxes. Doing so is the
single worst bug in this repo's history: it flattened 76 glyphs into solid rectangles. See
`docs/research/ground-truth-flattening.md`.

## Key Directories

| Path | Purpose |
|---|---|
| `src/vietfont/` | The tool. 14 modules, no subpackages. |
| `fonts/departure-mono-viet/` | The font project: sources, mark pack, builds, legacy pipeline. |
| `fonts/departure-mono-viet/font-src/` | Upstream font, unmodified (byte-identical to upstream v1.500). |
| `fonts/departure-mono-viet/build/` | Font artifacts. `DepartureMonoViet-Regular.otf` is the release. |
| `fonts/departure-mono-viet/legacy/` | Hand-built reference pipeline. **Not** the tool's code. |
| `docs/plans/active/` | Locked phase plan (`vietfont-v1.md`). |
| `docs/research/` | Experiment logs and bug post-mortems. Read before changing mark geometry. |
| `scripts/` | `make-demo.py` only. |

## Development Commands

```bash
# Setup — --system-site-packages is mandatory (see Runtime/Tooling below)
uv venv --python /opt/homebrew/bin/python3 --system-site-packages .venv
VIRTUAL_ENV=.venv uv pip install -e .
source .venv/bin/activate          # or prefix every command with .venv/bin/
vietfont --version

# The five commands
vietfont analyze <font>
vietfont add <font> -o <out> --marks <pack> --family "Departure Mono Viet" --ascent 600
vietfont verify <out> --source <font> --marks <pack>     # the gate; exit 1 on failure
vietfont proof <out> -o proof.html --layout columns      # human review
vietfont judge <out> --marks <pack>                      # advisory only

# Full rebuild + gate for the shipped font
vietfont add fonts/departure-mono-viet/font-src/DepartureMono-Regular.otf \
  -o fonts/departure-mono-viet/build/DepartureMonoViet-Regular.otf \
  --marks fonts/departure-mono-viet/marks.json \
  --family "Departure Mono Viet" --ascent 600
vietfont verify fonts/departure-mono-viet/build/DepartureMonoViet-Regular.otf \
  --source fonts/departure-mono-viet/font-src/DepartureMono-Regular.otf \
  --marks fonts/departure-mono-viet/marks.json

# Demo page (needs .venv/bin/vietfont and git; reads HEAD~5 for the old mark pack)
python scripts/make-demo.py

# Legacy reference pipeline — run from fonts/departure-mono-viet/, in this order
fontforge -script legacy/build_easy.py
fontforge -script legacy/scaffold_hard.py
fontforge -script legacy/finish_hard.py
fontforge -script legacy/copy_ligature_glyphs.py
```

There is **no lint or format command** — no ruff/mypy/black config is committed.

## Code Conventions & Common Patterns

- **`from __future__ import annotations`** at the top of every module that has code (12 of 13;
  `__init__.py` is only a version constant).
- **Docstrings in Vietnamese**, using RST directives (`:data:`, `:class:`). They carry domain
  rationale and bug history, not restatements of the signature. Match this — a docstring that says
  what the code obviously does is noise here.
- **Modern typing**: `list[str]`, `dict[str, int]`, `tuple[float, float]`, `str | Path`,
  `float | None`. No `typing.List`/`Optional`.
- **Naming**: `snake_case` functions/vars, `CamelCase` classes and dataclasses, `UPPER_SNAKE`
  constants, `_leading_underscore` for private helpers (`_dedupe`, `_shares_rows`, `_flattened`).
- **Import order**: stdlib → external (`fontforge`, `fontTools`, `typesafe_sdk`) → internal.
- **No async anywhere.** This is a synchronous CLI; `fontforge` is a blocking C extension.
- **No DI framework.** Modules take explicit parameters (`compose(font, char, pack, grid)`). Pass
  what a function needs; do not introduce a container.
- **State lives in dataclasses.** `Grid` and `Analysis` are `frozen=True`; `Composition`,
  `MarkPack`, `VerifyReport`, and `BuildReport` are mutable.
- **Errors**: `ComposeError` for composition failures. The CLI catches and reports; it does not
  raise tracebacks at the user.
- **Exit codes**: `analyze`/`proof` → 0. `add` → 0 if no glyph failed, else 1. `verify` → 0 if
  `report.ok`, else 1. `judge` → 1 if the font has no diacritic glyphs, else 0.

### Invariants that will bite you

1. **Winding must match.** Every mark contour must wind the same direction as its carrier
   (`ensure_winding`). Mismatched winding makes the nonzero fill rule cancel the overlap and punch
   holes in the glyph.
2. **`_dedupe` runs *before* `_shares_rows`, and again after compacting.** The actual order in
   `compose()` is: `_tone_shift` → `_dedupe` → `_shares_rows` → (if rows are shared) compact the
   carrier → `_dedupe` again. `_dedupe` drops mark contours identical to the carrier and absorbs
   carrier contours that fall inside a mark (the dot of `i`); `_shares_rows` then decides whether
   the carrier must be compacted. Note that `docs/research/mark-placement.md` states the opposite
   order — trust the code, and re-check that doc if you touch this path.
3. **Never flatten contours.** Preserve every vertex. See `docs/research/ground-truth-flattening.md`.
4. **Row-sharing, not bounding boxes, for 2-mark uppercase.** Marks interleave by column, so 2D
   bbox tests miss collisions. `_shares_rows()` compares grid-row occupancy and triggers the compact
   modifier. Without it `Ấ` and `Ẩ` render identically.
5. **`set_ascent` must update three fields together**: `os2_typoascent`, `hhea_ascent`,
   `os2_winascent`. Different OSes clip from different tables.
6. **`rename` must update nameID 1 *and* 16** (plus 2, 3, 4, 6, 17). macOS keys on 16.
7. **A generated `.fea` must declare `languagesystem latn dflt;`, not just `DFLT`.** With only
   `DFLT`, `liga` lands in the GSUB and `hb-shape` (default script) substitutes — but browsers
   resolve Latin text to `latn` and never ligate. `hb-shape --script=latn` is the test that
   catches it. See `docs/research/ligature-audit.md`.

## Important Files

| File | Why it matters |
|---|---|
| `src/vietfont/cli.py` | Entry point (`main`). All argparse definitions and exit codes. |
| `src/vietfont/compose.py` | The hard part: carrier + mark assembly, all six invariants above. |
| `src/vietfont/verify.py` | The gate. `VerifyReport.ok` defines pass/fail. |
| `src/vietfont/grid.py` | Grid detection; everything geometric depends on it. |
| `src/vietfont/glyph.py` | Contour read/write, signed area, winding. |
| `src/vietfont/build.py` | fontforge writes + the fontTools `rename()` patch. |
| `src/vietfont/judge.py` | Jev client. Read its module docstring before touching it. |
| `src/vietfont/ligatures.py` | Ligature import: grid snap, advance fix, `liga` feature. Enabled in the release; glyph quality is uneven. |
| `src/vietfont/charset.py` | The 134-character target set and Unicode decomposition. |
| `fonts/departure-mono-viet/marks.json` | Mark geometry. Four keys: `marks`, `compact_marks`, `modifiers`, `compact_modifiers`. |
| `pyproject.toml` | Hatchling, entry point, deps. |
| `NOTICE` | Which paths are OFL vs MIT. Read before adding files. |

`marks.json` shape format — a mark is a list of contours, each a list of `[x, y]` pairs:

```json
"hook_above": [
  [[100, 450], [250, 450], [250, 500], [100, 500]],
  [[200, 400], [250, 400], [250, 450], [200, 450]]
]
```

## Runtime/Tooling Preferences

- **Python ≥ 3.12** (`requires-python`); developed on Homebrew Python 3.14.
- **`uv`** for venv and installs. `VIRTUAL_ENV=.venv uv pip install -e .`
- **`fontforge` is a system module, not a pip package.** It is a C extension shipped with the
  Homebrew fontforge install. The venv **must** be created with `--system-site-packages` against
  Homebrew's Python, or `import fontforge` fails. This is the #1 setup failure.
- **Build backend**: hatchling. Package layout `src/vietfont`; entry point
  `vietfont = "vietfont.cli:main"`.
- **Dependencies**: `fonttools>=4.65`, `typesafe-sdk>=0.7`.
- **`judge` needs TypeSafe credentials.** Everything else runs offline.
- **FontForge caches glyph state in-process.** A verifier that checks a font it just wrote in the
  same process may read stale data — re-open from disk. See `docs/research/contour-nesting.md`.
- **Monospace only.** Pitch detection assumes a uniform advance from `a`/`o`/`O`. Proportional fonts
  are out of scope.
- **Vietnamese NFC only.** The target set is fixed at 134 characters in `charset.py`.

## Testing & QA

**There is no unit-test suite and no CI.** Do not look for one, and do not add a test framework
without being asked — this repo's verification model is deliberate.

The gate is `vietfont verify`, which is deterministic and returns exit 1 on any failure:

| Check | Compares | Requires |
|---|---|---|
| coverage | target charset vs font cmap | — |
| `flattened` | base contours vs `--source` — passes if identical *or* pixel footprint covered | `--source` |
| `duplicates` | rasterized cell sets across glyphs | `--source` |
| `gaps` | mark-to-base row gap (diagnostic only) | `--source` |
| `ink_diff` | rasterized cells vs `compose()` expectation | `--source` + `--marks` |
| `collisions` | mark/base contour overlap | `--source` + `--marks` |
| `ligatures` | GSUB substitution + on-grid + advance = `pitch × cols × n` | `--ligatures` (+ `path`) |

`VerifyReport.ok` is `not (missing or flattened or ink_diff or collisions or duplicates or
ligatures)`. Note `gaps` is a histogram, not a failure condition.

**Run `verify` with both `--source` and `--marks`.** Without them it degrades to a shallow codepoint
presence check that will happily pass a broken font.

**Grid detection runs on the output font, not the source** (`verify.py:53-56`), because `--ascent`
changes the row count. Do not "fix" this to use the source grid.

Human review is the final gate: `vietfont proof` writes a self-contained HTML sheet (fonts embedded
as base64 data URIs, no network) in `stack`, `columns`, or `focus` layout. `judge` may be run
alongside it to rank glyphs for the reviewer, but its output must never be wired into a pass/fail
decision.

When changing mark geometry, the expected end state is:

```
coverage : 134/134
shape    : 134/134 glyph giữ contour chữ nền
trùng hình: không có
mực      : khớp thiết kế
va chạm  : không có
ĐẠT
```
