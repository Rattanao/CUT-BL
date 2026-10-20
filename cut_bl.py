"""CUT BL: delete a B/L range from an HMAN EDI file (KMGY_2608S__THLCH_HMAN95.txt).

    python cut_bl.py <first B/L to delete> [folder] [--to <last B/L to delete>]

Deletes the lines from the H02 of the first B/L through the last line (H03 … H10)
of the last B/L and its sub-B/Ls; everything else is kept. The header lines (HOU,
H01) always stay - ECS-Manifest rejects the file without them ("invalid MMAN Text
File"). No --to = delete through the last line.
Result: <folder>/output/<name before "__">_PORTAL.txt, e.g. KMGY_2608S_PORTAL.txt.
The source file is never modified; bytes and CRLF are kept as-is.
"""
import argparse
import sys
from pathlib import Path


def find_one(folder: Path) -> Path:
    hits = sorted(folder.glob("*.txt"))
    if len(hits) != 1:
        sys.exit(f"ERROR: need exactly 1 .txt in {folder}, found {len(hits)}: {[h.name for h in hits]}")
    return hits[0]


def out_name(src: Path) -> str:
    """KMGY_2608S__THLCH_HMAN95.txt -> KMGY_2608S_PORTAL.txt"""
    return src.stem.split("__")[0] + "_PORTAL.txt"


def cut(raw: bytes, first_bl: str, last_bl: str = ""):
    """Delete the lines from the H02 of B/L `first_bl` through the last line of B/L `last_bl`
    (with its sub-B/Ls …A, …B); the header (HOU, H01) and the other B/Ls stay.
    Blank first = from the first H02, blank last = to the end.
    Returns (data, lines kept, total lines, B/Ls deleted, B/Ls kept)."""
    lines = raw.splitlines(keepends=True)

    def bl_at(i):
        return lines[i][3:38].strip().decode("latin-1").upper() if lines[i].startswith(b"H02") else None

    def in_group(bl, key):
        return bl == key or (len(bl) == len(key) + 1 and bl.startswith(key) and bl[-1].isalpha())

    first_bl, last_bl = first_bl.strip().upper(), last_bl.strip().upper()
    # "H02HASLC…" typed as-is is fine too
    first_bl = first_bl[3:] if first_bl.startswith("H02") else first_bl
    last_bl = last_bl[3:] if last_bl.startswith("H02") else last_bl

    start = next((i for i in range(len(lines)) if bl_at(i) and (not first_bl or bl_at(i) == first_bl)), None)
    if start is None:
        sys.exit(f"ERROR: start B/L {first_bl or '(H02)'} not found in the file")
    stop = len(lines)
    if last_bl:
        hits = [i for i in range(start, len(lines)) if bl_at(i) and in_group(bl_at(i), last_bl)]
        if not hits:
            sys.exit(f"ERROR: end B/L {last_bl} not found after start B/L {first_bl or '(first)'}")
        stop = hits[-1] + 1
        while stop < len(lines) and not bl_at(stop):
            stop += 1
    kept = lines[:start] + lines[stop:]  # start is an H02, so HOU / H01 always stay
    bls = lambda r: [bl_at(i) for i in r if bl_at(i)]
    return (b"".join(kept), len(kept), len(lines), bls(range(start, stop)),
            bls(list(range(start)) + list(range(stop, len(lines)))))


def main():
    ap = argparse.ArgumentParser(description="Delete a B/L range -> output/<name>_PORTAL.txt")
    ap.add_argument("bl", help="first B/L to delete, e.g. HASLC03260602093")
    ap.add_argument("folder", nargs="?", default=".", help="folder holding input/ (default: current folder)")
    ap.add_argument("--to", default="", help="last B/L to delete (with its sub-B/Ls); default: to the last line")
    a = ap.parse_args()

    folder = Path(a.folder).resolve()
    inp = next((d for d in (folder / "input", folder / "Input") if d.is_dir()), folder)
    src = find_one(inp)
    out = folder / "output" / out_name(src)
    out.parent.mkdir(exist_ok=True)

    data, kept, total, gone, left = cut(src.read_bytes(), a.bl, a.to)
    out.write_bytes(data)
    print(f"IN      : {src}\nOUT     : {out}")
    print(f"Cut     : removed {total - kept} lines ({total} -> {kept})")
    print(f"Deleted : {len(gone)} B/L ({gone[0]} to {gone[-1]})")
    print(f"Left    : {len(left)} B/L {left}")


if __name__ == "__main__":
    main()
