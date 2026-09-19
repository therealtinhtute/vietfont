"""Command line entry point for vietfont."""

from __future__ import annotations

import argparse
from pathlib import Path

import fontforge

from vietfont import __version__
from vietfont import charset as cs
from vietfont.analyze import analyze
from vietfont.build import extend, save
from vietfont.marks import MarkPack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vietfont",
        description="Việt hoá font pixel/bitmap: code dựng glyph, Jev phán, người duyệt ca khó.",
    )
    parser.add_argument("--version", action="version", version=f"vietfont {__version__}")
    commands = parser.add_subparsers(dest="command")

    analyze_cmd = commands.add_parser("analyze", help="đo độ phủ tiếng Việt của font")
    analyze_cmd.add_argument("font", help="đường dẫn font nguồn")

    add_cmd = commands.add_parser("add", help="dựng các ký tự tiếng Việt còn thiếu")
    add_cmd.add_argument("font", help="đường dẫn font nguồn")
    add_cmd.add_argument("-o", "--output", required=True, help="đường dẫn font xuất")
    add_cmd.add_argument("--marks", help="mark pack JSON cho mark/modifier mà font thiếu")

    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _run_analyze(args)
    if args.command == "add":
        return _run_add(args)

    parser.print_help()
    return 0


def _run_analyze(args: argparse.Namespace) -> int:
    font = fontforge.open(args.font)
    result = analyze(font)
    total = len(cs.charset())

    print(f"font     : {args.font}")
    print(f"lưới     : {result.grid.cols}×{result.grid.rows} ô, pitch {result.grid.pitch}, đỉnh {result.grid.top}")
    print(f"tiếng Việt: {len(result.present)}/{total} có sẵn, thiếu {len(result.missing)}")
    if result.missing_carriers:
        print(f"thiếu carrier: {''.join(result.missing_carriers)}")
    if result.missing_marks:
        print(f"thiếu mark   : {', '.join(result.missing_marks)}")
    if result.complete:
        print("font đã đủ bộ ký tự tiếng Việt")
    return 0


def _run_add(args: argparse.Namespace) -> int:
    font = fontforge.open(args.font)
    pack = MarkPack.load(args.marks) if args.marks else MarkPack()

    report = extend(font, pack)
    save(font, args.output)

    print(f"đã thêm  : {len(report.added)} glyph")
    print(f"bỏ qua   : {len(report.skipped)} glyph đã có sẵn")
    if report.collisions:
        print(f"va chạm  : {len(report.collisions)} glyph có dấu đè lên chữ nền")
        for char, count in sorted(report.collisions.items()):
            print(f"           {char}  ({count} cặp contour)")
    if report.failed:
        print(f"lỗi      : {len(report.failed)} glyph không dựng được")
        for char, reason in sorted(report.failed.items()):
            print(f"           {char}  {reason}")
    print(f"xuất     : {args.output}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
