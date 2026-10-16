"""JLCPCB placement file (CPL) fitted part by part on JLC's own footprints, or check of an existing one.

    KPY jlc_cpl.py board.kicad_pcb --bom BOM.csv -o CPL.csv          # write the CPL
    KPY jlc_cpl.py board.kicad_pcb --bom BOM.csv --check CPL.csv     # check a CPL made elsewhere

JLC places each part with ITS footprint: the EasyEDA/LCSC footprint of the part number in the BOM. It
puts that footprint's origin on the CPL point and turns it by the CPL angle, counter-clockwise seen from
the top. Neither the origin nor the zero angle match KiCad's, and they change from one part number to
another inside the same package: one SOT-23-6 sits 90 degrees from a SOT-23 of another maker. Fixed
per-package rotation tables are therefore wrong for some parts, and nothing in KiCad shows it.

So nothing is guessed. For each part, the EasyEDA footprint of its LCSC number is downloaded (cached),
the four rotations are tried, and the one that lays its pads on the board's pads, pin number by pin
number, wins; the position follows. A part that does not fit within --tol mm is reported and falls back
to the KiCad position and angle: check it in JLC's "Component Placements" preview.

LCSC numbers come from the BOM (columns Designator and "LCSC Part #", or "LCSC", "JLCPCB Part #"), or
else from an "LCSC" field on the footprint. Top side only: bottom parts are reported and skipped.
The EasyEDA server refuses bursts of requests (HTTP 403): the cache avoids downloading a part twice.
"""
import argparse
import csv
import json
import math
import re
import subprocess
from pathlib import Path

import pcbnew

from kicad_common import MM

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("--bom", help="BOM CSV with Designator and LCSC columns")
ap.add_argument("-o", "--out", help="CPL to write")
ap.add_argument("--check", help="existing CPL to check instead of writing one")
ap.add_argument("--cache", help="folder for downloaded EasyEDA footprints (default: easyeda/ beside the output)")
ap.add_argument("--tol", type=float, default=0.6, help="largest pad spread accepted, mm (pad length differences)")
ap.add_argument("--shift", type=float, default=0.15, help="largest whole-part shift accepted by --check, mm")
a = ap.parse_args()
if not (a.out or a.check):
    ap.error("give -o to write a CPL or --check to check one")
cache = Path(a.cache) if a.cache else Path(a.out or a.check).resolve().parent / "easyeda"


def jlc_pads(code):
    """Pads of the EasyEDA footprint of an LCSC number: {number: [(x, y) mm]}, Y up, origin = JLC's."""
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{code}.json"
    if not f.exists():
        # through curl: the server answers 403 to Python's urllib whatever the User-Agent
        url = f"https://easyeda.com/api/products/{code}/components?version=6.4.19.5"
        r = subprocess.run(["curl", "-sf", "-m", "30", "-o", str(f), url])
        if r.returncode:
            f.unlink(missing_ok=True)
            return None
    d = json.loads(f.read_text(encoding="utf-8"))["result"]["packageDetail"]["dataStr"]
    ox, oy = float(d["head"]["x"]), float(d["head"]["y"])
    pads = {}
    for s in d["shape"]:
        if s.startswith("PAD~"):
            c = s.split("~")    # PAD~shape~x~y~width~height~layer~net~number~...  in units of 10 mil
            pads.setdefault(c[8], []).append(((float(c[2]) - ox) * 0.254, -(float(c[3]) - oy) * 0.254))
    return pads


def turn(p, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return p[0] * c - p[1] * s, p[0] * s + p[1] * c


def board_pads(fp):
    out = {}
    for p in fp.Pads():
        q = p.GetPosition()
        out.setdefault(p.GetNumber(), []).append((MM(q.x), -MM(q.y)))
    return out


def residuals(kp, jp, x, y, deg):
    """(shift, spread) of JLC's footprint placed at (x, y, deg) against the board's pads, in mm.
    shift: how far the part sits from where it should, as a whole. spread: how badly the pads disagree
    once that shift is removed (wrong angle, or pads of another length, as on many SOIC footprints)."""
    common = [n for n in kp if n in jp and len(kp[n]) == 1 and len(jp[n]) == 1]
    if not common:
        return None
    v = [(kp[n][0][0] - x - turn(jp[n][0], deg)[0], kp[n][0][1] - y - turn(jp[n][0], deg)[1]) for n in common]
    mx, my = sum(e[0] for e in v) / len(v), sum(e[1] for e in v) / len(v)
    return math.hypot(mx, my), max(math.hypot(e[0] - mx, e[1] - my) for e in v)


def fit(kp, jp):
    """(x, y, angle, worst mm) laying JLC's footprint on the board's pads, or None."""
    # pins present once on both sides: mounting tabs are often numbered differently
    common = [n for n in kp if n in jp and len(kp[n]) == 1 and len(jp[n]) == 1]
    if len(common) < 2:
        return None
    best = None
    for deg in (0, 90, 180, 270):
        dx = [kp[n][0][0] - turn(jp[n][0], deg)[0] for n in common]
        dy = [kp[n][0][1] - turn(jp[n][0], deg)[1] for n in common]
        x, y = sum(dx) / len(dx), sum(dy) / len(dy)
        worst = residuals(kp, jp, x, y, deg)[1]
        if best is None or worst < best[3]:
            best = (x, y, deg, worst)
    return best


lcsc = {}
if a.bom:
    for row in csv.DictReader(open(a.bom, encoding="utf-8-sig")):
        code = next((row[k] for k in ("LCSC Part #", "LCSC", "JLCPCB Part #", "LCSC Part") if row.get(k)), "")
        for ref in re.split(r"[,\s]+", row.get("Designator", "")):
            if ref and code:
                lcsc[ref] = code.strip()
board = pcbnew.LoadBoard(a.board)
for fp in board.GetFootprints():
    for fld in fp.GetFields():
        if fld.GetName() in ("LCSC", "LCSC Part #") and fld.GetText() and fp.GetReference() not in lcsc:
            lcsc[fp.GetReference()] = fld.GetText().strip()


def natural(ref):
    return re.sub(r"\d+", "", ref), int(re.sub(r"\D", "", ref) or 0)


if a.check:
    bad = 0
    for row in csv.DictReader(open(a.check, encoding="utf-8-sig")):
        ref = row["Designator"]
        fp = board.FindFootprintByReference(ref)
        jp = jlc_pads(lcsc[ref]) if ref in lcsc and fp else None
        if not jp:
            print(f"{ref:5} not checked (no footprint, LCSC number or EasyEDA data)")
            continue
        x, y = float(row["Mid X"].rstrip("m")), float(row["Mid Y"].rstrip("m"))
        res = residuals(board_pads(fp), jp, x, y, float(row["Rotation"]))
        ok = res is not None and res[0] <= a.shift and res[1] <= a.tol
        bad += not ok
        good = fit(board_pads(fp), jp)
        hint = f"  -> should be {good[0]:.3f} {good[1]:.3f} rot {good[2]:g}" if not ok and good else ""
        print(f"{ref:5} {lcsc[ref]:10} " + (f"shift {res[0]:.2f} mm, spread {res[1]:.2f} mm" if res else "no common pin")
              + f" {'ok' if ok else 'WRONG'}{hint}")
    print(f"{bad} part(s) misplaced")
    raise SystemExit(1 if bad else 0)

rows, warnings = [], []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES:
        continue
    if ref not in lcsc:
        continue                      # not assembled (no LCSC number): test points, holes, logos
    if fp.IsFlipped():
        warnings.append(f"{ref}: bottom side, not in this CPL")
        continue
    jp = jlc_pads(lcsc[ref])
    good = fit(board_pads(fp), jp) if jp else None
    if good and good[3] <= a.tol:
        x, y, deg = good[0], good[1], good[2]
    else:
        warnings.append(f"{ref} ({lcsc[ref]}): not fitted on JLC's footprint"
                        f"{f' (worst pad {good[3]:.2f} mm)' if good else ''}, KiCad position kept: check the preview")
        x, y, deg = MM(fp.GetPosition().x), -MM(fp.GetPosition().y), fp.GetOrientationDegrees() % 360
    rows.append([ref, f"{x:.3f}mm", f"{y:.3f}mm", "Top", f"{deg:g}"])
rows.sort(key=lambda r: natural(r[0]))
with open(a.out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    w.writerows(rows)
print(f"{len(rows)} parts written to {a.out}")
for m in warnings:
    print("WARNING", m)
