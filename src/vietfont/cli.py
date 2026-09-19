"""Command line entry point for vietfont."""

from __future__ import annotations

import argparse
from pathlib import Path

import fontforge

from vietfont import __version__
from vietfont import charset as cs
from vietfont.analyze import analyze
from vietfont.build import collisions, extend, save
from vietfont.grid import Grid
from vietfont.judge import ADVISORY_THRESHOLD, verify_marks
from vietfont.marks import MarkPack
from vietfont.proof import LAYOUTS, ProofFont, ProofSheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vietfont",
        description="Việt hoá font pixel/bitmap: code dựng glyph, Jev phán, người duyệt ca khó.",
    )
    parser.add_argument(
        "--version", action="version", version=f"vietfont {__version__}"
    )
    commands = parser.add_subparsers(dest="command")

    analyze_cmd = commands.add_parser("analyze", help="đo độ phủ tiếng Việt của font")
    analyze_cmd.add_argument("font", help="đường dẫn font nguồn")

    add_cmd = commands.add_parser("add", help="dựng các ký tự tiếng Việt còn thiếu")
    add_cmd.add_argument("font", help="đường dẫn font nguồn")
    add_cmd.add_argument("-o", "--output", required=True, help="đường dẫn font xuất")
    add_cmd.add_argument(
        "--marks", help="mark pack JSON cho mark/modifier mà font thiếu"
    )

    judge_cmd = commands.add_parser(
        "judge",
        help="hỏi Jev về tone mark — tín hiệu tham khảo, không phải cổng verify",
    )
    judge_cmd.add_argument("font", help="đường dẫn font cần kiểm")
    judge_cmd.add_argument("--marks", required=True, help="mark pack JSON")

    proof_cmd = commands.add_parser(
        "proof", help="xuất proof sheet HTML để duyệt bằng mắt"
    )
    proof_cmd.add_argument("font", help="đường dẫn font cần duyệt")
    proof_cmd.add_argument("-o", "--output", required=True, help="đường dẫn HTML xuất")
    proof_cmd.add_argument("--label", default="vietfont", help="nhãn của font chính")
    proof_cmd.add_argument(
        "--compare",
        action="append",
        default=[],
        help="font khác để đặt cạnh (lặp lại được)",
    )
    proof_cmd.add_argument("--marks", help="mark pack JSON, để quét glyph có va chạm")
    proof_cmd.add_argument(
        "--source", help="font gốc để quét va chạm (mặc định: chính font đang duyệt)"
    )
    proof_cmd.add_argument(
        "--layout",
        default="columns",
        choices=LAYOUTS,
        help="kiểu trình bày proof sheet",
    )

    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _run_analyze(args)
    if args.command == "add":
        return _run_add(args)
    if args.command == "judge":
        return _run_judge(args)
    if args.command == "proof":
        return _run_proof(args)

    parser.print_help()
    return 0


def _run_analyze(args: argparse.Namespace) -> int:
    font = fontforge.open(args.font)
    result = analyze(font)
    total = len(cs.charset())

    print(f"font     : {args.font}")
    print(
        f"lưới     : {result.grid.cols}×{result.grid.rows} ô, pitch {result.grid.pitch}, đỉnh {result.grid.top}"
    )
    print(
        f"tiếng Việt: {len(result.present)}/{total} có sẵn, thiếu {len(result.missing)}"
    )
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


def _run_judge(args: argparse.Namespace) -> int:
    font = fontforge.open(args.font)
    pack = MarkPack.load(args.marks)
    grid = Grid.detect(font)

    results = verify_marks(font, grid, pack)
    if not results:
        print(f"font     : {args.font}")
        print("không có glyph nào có thanh điệu — chạy `vietfont add` trước")
        return 1

    agree = sum(j.agrees for j in results)
    unsure = [j for j in results if not j.trustworthy]

    print(f"font     : {args.font}")
    print(f"đã hỏi   : {len(results)} glyph có thanh điệu")
    print(f"đồng ý   : {agree}/{len(results)} ({100 * agree / len(results):.0f}%)")
    print(f"conf thấp: {len(unsure)} glyph (dưới {ADVISORY_THRESHOLD})")
    print()
    print(
        "LƯU Ý: Jev chỉ đạt ~80% ở câu hỏi này — đây là tín hiệu tham khảo để xếp hạng"
    )
    print(
        "glyph cho người xem, KHÔNG phải cổng verify. Xem docs/research/jev-verification-limits.md"
    )
    if unsure:
        print(f"\nglyph nên xem trước: {' '.join(j.char for j in unsure)}")
    return 0


def _run_proof(args: argparse.Namespace) -> int:
    fonts = [ProofFont(label=args.label, path=args.font)]
    for index, path in enumerate(args.compare, start=1):
        fonts.append(ProofFont(label=f"so sánh {index}: {Path(path).name}", path=path))

    flagged: list[str] = []
    if args.marks:
        font = fontforge.open(args.source or args.font)
        flagged = sorted(collisions(font, MarkPack.load(args.marks)))

    sheet = ProofSheet(
        title="Departure Mono Việt — proof sheet",
        fonts=fonts,
        flagged=flagged,
        layout=args.layout,
    )
    target = sheet.write(args.output)

    print(f"proof sheet: {target}")
    print(f"layout     : {args.layout}")
    print(f"font đưa vào: {len(fonts)}")
    if flagged:
        print(f"glyph va chạm: {len(flagged)} — {' '.join(flagged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
