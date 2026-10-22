---
name: cut-bl
description: "CUT BL" for a Thailand import HMAN EDI file (HOU/H01/H02…H10 records, e.g. KMGY_2608S__THLCH_HMAN95.txt). Deletes the B/L range the user names, "เริ่มตัด B/L … ถึง B/L …" (e.g. HASLC03260602093 to HASLC03260701048): from the H02 line of the first B/L through the last line (H03…H10) of the last B/L and its sub-B/Ls, keeping the HOU/H01 header lines and every other B/L; or keeps only the B/Ls the user lists, comma separated ("เก็บ HASLJ01260800588,HASLK02261000346"), cutting all other B/Ls. On every B/L left, H05 (consignee) is set to the H06 (notify) name with single spaces only, and the H07 package unit PG becomes PX. Writes output/<name before "__">_PORTAL.txt (e.g. KMGY_2608S_PORTAL.txt). Use whenever the user says "cut bl", "ตัด BL", "ตัด HMAN", "เริ่มตัดที่ H02", "ทำไฟล์ PORTAL", "เก็บ BL …", or points to a folder with input/ holding an HMAN .txt and names B/Ls to cut.
---

# CUT BL (ลบช่วง B/L หรือเก็บเฉพาะ B/L → output/<name>_PORTAL.txt)

Rattana's confirmed format. Run the bundled script; don't edit the file by hand. The file is
fixed-width, latin-1 and CRLF. Never change line lengths or line endings.

## File layout

```
HOU8858888002119…      ← header, always kept
H01                    ← header, always kept
H02HASLC03260602093 …  ← one B/L starts (B/L no. = col 3-37)
H03 … H10              ← the rest of that B/L (H09 = containers, may repeat; H08 may repeat)
H02HASLC03260602438 …  ← next B/L
```

## Rules (confirmed by Rattana)

- **"ตัด" = DELETE.** The named range is removed; what is left is everything outside it.
  (An early version kept the range and dropped the rest. That was wrong.)
- Delete from the **H02** line of the first B/L through the last line (H03…H10) of the last
  B/L, including its sub-B/Ls (`…048A`, `…048B`).
- **Keep mode ("เก็บ B/L …", comma separated, 1 or more):** keep only those B/Ls (each from
  its H02 to the line before the next H02, with sub-B/Ls), in file order; delete all other B/Ls.
  Range and keep mode are used one at a time, never both.
- **No B/L at all = no cut** (`--all`, or every web field blank): only the H05 / H07 fixes.
  Use it only when the user asks for that; otherwise ask which B/Ls.
- **On every B/L left** (both modes):
  - `H05` = the `H06` name (from col 5) with single spaces only, padded with spaces to the H06
    line length. `H05TH` (cols 0-4) stays; `H06` itself is never changed.
  - `H07` package unit (cols 10-11) `PG` → `PX`, e.g. `H070000100PG` → `H070000100PX`.
- **Always keep `HOU…` and `H01`.** Without them ECS-Manifest (Import MMAN, "01 - Import EDI
  FLat File") says *"This file is invalid MMAN Text File"*.
- B/L may be typed as `HASLC…` or `H02HASLC…`. No first B/L = from the first H02. No last B/L
  = through the last line.
- Output name = the source file name before `__` + `_PORTAL.txt`
  (`KMGY_2608S__THLCH_HMAN95.txt` → `KMGY_2608S_PORTAL.txt`), in `output/`. The file name
  is not what ECS checks.
- Bytes and CRLF are copied as-is. The source file is never modified.

## Input

- A folder with `input/` (or `Input/`) containing **1** `.txt` HMAN file.
- Either the first B/L to cut ("เริ่มตัด B/L") and optionally the last ("ถึง B/L"), or the
  B/Ls to keep ("เก็บ …", comma separated). If the user gave no B/L, ask. Don't guess.

## Steps

1. Run:
   ```bash
   PYTHONIOENCODING=utf-8 python "<skill dir>/scripts/cut_bl.py" <first B/L> "<folder containing input>" [--to <last B/L>]
   ```
   or, to keep only some B/Ls:
   ```bash
   PYTHONIOENCODING=utf-8 python "<skill dir>/scripts/cut_bl.py" --keep <B/L>,<B/L> "<folder containing input>"
   ```
   (If `python` is only the Microsoft Store alias, use `py` instead.) No extra packages needed.
2. Report to the user in Thai: lines removed (total → left), the B/L range deleted (or the B/Ls kept) and how many, which B/Ls got H05 = H06 and which went PG → PX,
   B/Ls, the B/Ls left, the output file name. Show that `HOU` / `H01` are still on top.
3. If the script prints `ERROR` (B/L not found, more than one .txt in input), tell the user and
   ask. Don't guess.

Web version (same logic, runs in the browser): https://rattanao.github.io/CUT-BL/
