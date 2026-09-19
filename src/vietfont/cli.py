"""Command line entry point for vietfont."""

from __future__ import annotations

import argparse

from vietfont import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vietfont",
        description="Việt hoá font pixel/bitmap: code dựng glyph, Jev phán, người duyệt ca khó.",
    )
    parser.add_argument("--version", action="version", version=f"vietfont {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
