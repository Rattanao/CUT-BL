"""CUT BL: delete a B/L range from an HMAN EDI file (KMGY_2608S__THLCH_HMAN95.txt),
or keep only the B/Ls you name.

    python cut_bl.py <first B/L to delete> [folder] [--to <last B/L to delete>]
    python cut_bl.py --keep <B/L>,<B/L>,... [folder]

Range: deletes the lines from the H02 of the first B/L through the last line (H03 … H10)
of the last B/L and its sub-B/Ls; everything else is kept. No --to = delete through
the last line.
--keep: keeps only the named B/Ls (with their sub-B/Ls), in file order; every other
B/L is deleted.
Either way the header lines (HOU, H01) always stay - ECS-Manifest rejects the file
without them ("invalid MMAN Text File").
Then on every B/L left: H05 (consignee) = the H06 (notify) name with single spaces only
(cols 0-4 "H05TH" kept, H06 itself untouched), and H07 package unit PG -> PX.
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


def norm_bl(bl: str) -> str:
    """H02HASLC… / haslc… -> HASLC…"""
    bl = bl.strip().upper()
    return bl[3:].strip() if bl.startswith("H02") else bl


def in_group(bl, key):
    """B/L `bl` is `key` or one of its sub-B/Ls (…A, …B)"""
    return bl == key or (len(bl) == len(key) + 1 and bl.startswith(key) and bl[-1].isalpha())


def keep_only(raw: bytes, keys):
    """HOU / H01 + only the B/Ls in `keys` (with sub-B/Ls), each from its H02 to the line
    before the next H02. Returns (data, lines kept, total lines, B/Ls deleted, B/Ls kept)."""
    lines = raw.splitlines(keepends=True)
    h02 = [i for i, l in enumerate(lines) if l.startswith(b"H02")]
    if not h02:
        sys.exit("ERROR: no H02 line in the file")
    keys = [k for k in map(norm_bl, keys) if k]
    if not keys:
        sys.exit("ERROR: no B/L given to keep")
    kept, gone, left = lines[:h02[0]], [], []
    for s, e in zip(h02, h02[1:] + [len(lines)]):
        bl = lines[s][3:38].strip().decode("latin-1").upper()
        if any(in_group(bl, k) for k in keys):
            kept += lines[s:e]
            left.append(bl)
        else:
            gone.append(bl)
    missing = [k for k in keys if not any(in_group(bl, k) for bl in left)]
    if missing:
        sys.exit(f"ERROR: B/L not found in the file: {missing}")
    return b"".join(kept), len(kept), len(lines), gone, left


def fix_lines(data: bytes):
    """H05 = H06 name (from col 5) with single spaces, padded to the H06 line length;
    H07 package unit (col 10-11) PG -> PX. Returns (data, report)."""
    lines = data.splitlines(keepends=True)
    rep = {"h05": [], "h05_same": 0, "no_h06": [], "px": []}
    bl = None
    for i, l in enumerate(lines):
        if l.startswith(b"H02"):
            bl = l[3:38].strip().decode("latin-1")
        elif l.startswith(b"H05"):
            j = next((k for k in range(i + 1, len(lines)) if lines[k][:3] in (b"H06", b"H02")), None)
            if j is None or not lines[j].startswith(b"H06"):
                rep["no_h06"].append(bl)
                continue
            eol = l[len(l.rstrip(b"\r\n")):]
            h06 = lines[j].rstrip(b"\r\n")
            name = b" ".join(h06[5:].split())
            new = (l[:5] + name).ljust(len(h06)) + eol
            if new != l:
                lines[i] = new
                rep["h05"].append(bl)
            else:
                rep["h05_same"] += 1
        elif l.startswith(b"H07") and l[10:12] == b"PG":
            lines[i] = l[:10] + b"PX" + l[12:]
            rep["px"].append(bl)
    return b"".join(lines), rep


def cut(raw: bytes, first_bl: str, last_bl: str = ""):
    """Delete the lines from the H02 of B/L `first_bl` through the last line of B/L `last_bl`
    (with its sub-B/Ls …A, …B); the header (HOU, H01) and the other B/Ls stay.
    Blank first = from the first H02, blank last = to the end.
    Returns (data, lines kept, total lines, B/Ls deleted, B/Ls kept)."""
    lines = raw.splitlines(keepends=True)

    def bl_at(i):
        return lines[i][3:38].strip().decode("latin-1").upper() if lines[i].startswith(b"H02") else None

    first_bl, last_bl = norm_bl(first_bl), norm_bl(last_bl)

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
    ap = argparse.ArgumentParser(description="Delete a B/L range, or keep only some B/Ls -> output/<name>_PORTAL.txt")
    ap.add_argument("bl", nargs="?", default="", help="first B/L to delete, e.g. HASLC03260602093")
    ap.add_argument("folder", nargs="?", default=".", help="folder holding input/ (default: current folder)")
    ap.add_argument("--to", default="", help="last B/L to delete (with its sub-B/Ls); default: to the last line")
    ap.add_argument("--keep", default="", help="keep only these B/Ls, comma separated, e.g. HASLJ01260800588,HASLK02261000346")
    a = ap.parse_args()
    if a.keep and a.bl and a.folder == ".":  # cut_bl.py --keep X,Y <folder>
        a.folder, a.bl = a.bl, ""
    if a.keep and (a.bl or a.to):
        sys.exit("ERROR: use either a range (<first B/L> --to <last B/L>) or --keep, not both")
    if not a.keep and not a.bl:
        ap.error("give the first B/L to delete, or --keep <B/L>,<B/L>")

    folder = Path(a.folder).resolve()
    inp = next((d for d in (folder / "input", folder / "Input") if d.is_dir()), folder)
    src = find_one(inp)
    out = folder / "output" / out_name(src)
    out.parent.mkdir(exist_ok=True)

    if a.keep:
        data, kept, total, gone, left = keep_only(src.read_bytes(), a.keep.split(","))
    else:
        data, kept, total, gone, left = cut(src.read_bytes(), a.bl, a.to)
    data, rep = fix_lines(data)
    out.write_bytes(data)
    print(f"IN      : {src}\nOUT     : {out}")
    print(f"Mode    : {'keep only ' + a.keep.upper() if a.keep else 'delete range'}")
    print(f"Cut     : removed {total - kept} lines ({total} -> {kept})")
    print(f"Deleted : {len(gone)} B/L" + (f" ({gone[0]} to {gone[-1]})" if gone else ""))
    print(f"Left    : {len(left)} B/L {left}")
    print(f"H05=H06 : changed {rep['h05'] or 'none'}, already same {rep['h05_same']}")
    print(f"PG -> PX: {rep['px'] or 'none'}")
    if rep["no_h06"]:
        print(f"WARNING H05 without H06 (kept): {rep['no_h06']}")


if __name__ == "__main__":
    main()
