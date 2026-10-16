"""Full check of a KiCad board after a human save, read-only on the project.

    KPY board_check.py board.kicad_pcb [--prev older.kicad_pcb] [--gnd /GND] [--no-snapshot]

Prints, in this order:
  1. when the file was saved, and whether KiCad has it open;
  2. DRC on a temporary copy, zones refilled, with schematic parity: counts per type, every error,
     every unconnected item, every parity difference;
  3. totals: vias (ground vias), track length, near-zero segments, ground pour pieces per layer;
  4. what changed since the previous check: moved footprints, per-net length and via count;
  5. small ground islands, with the vias and ground pads they contain;
  6. decoupling: each capacitor between a net and ground, its distance to the nearest IC or connector
     pin on that net, whether its ground pad sits in the same pour piece as that part's ground pads,
     and the nearest ground via;
  7. vias touching or inside SMD pads.

Without --prev, the board is compared with the snapshot kept from the previous run
(<temp>/kicad-pcb-helper/<board name>/), which is then replaced. A board given with --prev needs its
.kicad_pro beside it, or its zones refill with default clearances and the pour areas are wrong.
"""
import argparse
import collections
import datetime
import glob
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pcbnew

from kicad_common import (MM, area_mm2, dist, edge_dist, fill_pieces, guess_gnd, kicad_cli, load, lock_file,
                          net_name, piece_of, tracks, vias)

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("--prev", help="board to compare with (default: snapshot of the previous run)")
ap.add_argument("--gnd", help="ground net name, e.g. /GND (default: net of the largest pour)")
ap.add_argument("--island-mm2", type=float, default=500, help="report ground pieces smaller than this")
ap.add_argument("--no-snapshot", action="store_true", help="do not read or update the snapshot")
a = ap.parse_args()
board = Path(a.board).resolve()

# --- 1. save time, lock ------------------------------------------------------------------
saved = datetime.datetime.fromtimestamp(board.stat().st_mtime)
print(f"saved {saved:%Y-%m-%d %H:%M:%S}" + ("   (open in KiCad: checking the last save)" if lock_file(board) else ""))

# --- 2. DRC on a copy, with the schematic for parity ------------------------------------------
tmp = Path(tempfile.mkdtemp(prefix="kph_"))
for f in [board.with_suffix(s) for s in (".kicad_pro", ".kicad_dru")] + [Path(p) for p in glob.glob(str(board.parent / "*.kicad_sch"))] \
        + [board.parent / n for n in ("sym-lib-table", "fp-lib-table")]:
    if f.exists():
        shutil.copy(f, tmp / f.name)
shutil.copy(board, tmp / board.name)
if not (tmp / board.with_suffix(".kicad_sch").name).exists():
    print("WARNING: no schematic next to the board: schematic parity NOT checked")
out = tmp / "drc.json"
subprocess.run([kicad_cli(), "pcb", "drc", "--refill-zones", "--schematic-parity", "--severity-all",
                "--format", "json", "-o", str(out), str(tmp / board.name)], capture_output=True)
d = json.loads(out.read_text(encoding="utf-8"))
counts = collections.Counter((v["severity"], v["type"]) for v in d["violations"])
print("DRC", dict(counts), "| unconnected", len(d["unconnected_items"]), "| parity", len(d["schematic_parity"]))
for v in d["violations"]:
    if v["severity"] == "error":
        print("  ERROR", v["description"], [(i["description"], round(i["pos"]["x"], 2), round(i["pos"]["y"], 2)) for i in v["items"]])
for v in d["unconnected_items"]:
    print("  UNCONNECTED", [(i["description"], round(i["pos"]["x"], 2), round(i["pos"]["y"], 2)) for i in v["items"]])
for v in d["schematic_parity"]:
    print("  PARITY", v["description"], [i["description"] for i in v["items"]])

# --- 3. totals -----------------------------------------------------------------------------
b = load(board)
gnd = net_name(b, a.gnd) if a.gnd else guess_gnd(b)


def summary(bd, name):
    vs = vias(bd)
    tr = tracks(bd)
    short = [t for t in tr if MM(t.GetLength()) < 0.02]
    pieces = collections.defaultdict(list)
    for layer, o in fill_pieces(bd, gnd):
        pieces[bd.GetLayerName(layer)].append(round(area_mm2(o)))
    print(f"{name}: vias {len(vs)} ({gnd} {sum(v.GetNetname() == gnd for v in vs)}) | tracks {sum(MM(t.GetLength()) for t in tr):.0f} mm"
          f" | near-zero segments {len(short)} | {gnd} pour pieces (mm2) {dict(pieces)}")
    return short


for t in summary(b, "now"):
    print(f"  near-zero segment {t.GetNetname()} {t.GetLayerName()} ({MM(t.GetStart().x):.2f}; {MM(t.GetStart().y):.2f})")

# --- 4. changes since the previous check ------------------------------------------------------
# the snapshot keeps the .kicad_pro beside it: without it, zones refill with default clearances
snap = Path(tempfile.gettempdir()) / "kicad-pcb-helper" / board.stem / board.name
prev = Path(a.prev) if a.prev else (snap if snap.exists() and not a.no_snapshot else None)
if prev:
    p = load(prev)
    summary(p, "prev")
    fa = {f.GetReference(): f for f in p.GetFootprints()}
    for f in b.GetFootprints():
        r = f.GetReference()
        o = fa.get(r)
        if o is None:
            print(f"  new {r}")
        elif o.GetPosition() != f.GetPosition() or o.GetOrientationDegrees() != f.GetOrientationDegrees() or o.IsFlipped() != f.IsFlipped():
            print(f"  moved {r:5} ({MM(o.GetPosition().x):.2f}; {MM(o.GetPosition().y):.2f} r{o.GetOrientationDegrees():g})"
                  f" -> ({MM(f.GetPosition().x):.2f}; {MM(f.GetPosition().y):.2f} r{f.GetOrientationDegrees():g}){'  flipped' if o.IsFlipped() != f.IsFlipped() else ''}")
    for r in sorted(set(fa) - {f.GetReference() for f in b.GetFootprints()}):
        print(f"  removed {r}")

    def per_net(bd):
        ln, nv = collections.defaultdict(float), collections.Counter()
        for t in bd.GetTracks():
            if t.GetClass() == "PCB_VIA":
                nv[t.GetNetname()] += 1
            else:
                ln[t.GetNetname()] += MM(t.GetLength())
        return ln, nv

    (la, va), (lb, vb) = per_net(p), per_net(b)
    for n in sorted(set(la) | set(lb) | set(va) | set(vb)):
        if abs(la[n] - lb[n]) > 0.3 or va[n] != vb[n]:
            print(f"  {n:14} {la[n]:.1f} -> {lb[n]:.1f} mm, vias {va[n]} -> {vb[n]}")
if not a.no_snapshot and not a.prev:
    snap.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(board, snap)
    if board.with_suffix(".kicad_pro").exists():
        shutil.copy(board.with_suffix(".kicad_pro"), snap.with_suffix(".kicad_pro"))

# --- 5. small ground islands ---------------------------------------------------------------
pieces = fill_pieces(b, gnd)
gvias = [v for v in vias(b) if v.GetNetname() == gnd]
gpads = [(f.GetReference(), p) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == gnd]
for layer, o in pieces:
    if area_mm2(o) < a.island_mm2:
        bb = o.BBox()
        inside = sorted({f"{r}-{p.GetNumber()}" for r, p in gpads if p.IsOnLayer(layer) and o.PointInside(p.GetPosition())})
        print(f"  island {b.GetLayerName(layer)} {area_mm2(o):.0f} mm2 at ({MM(bb.GetLeft()):.1f}; {MM(bb.GetTop()):.1f})-"
              f"({MM(bb.GetRight()):.1f}; {MM(bb.GetBottom()):.1f}), {sum(o.PointInside(v.GetPosition()) for v in gvias)} via(s),"
              f" ground pads: {', '.join(inside) or 'none'}")

# --- 6. decoupling -------------------------------------------------------------------------
PASSIVE = ("C", "R", "L", "FB", "TP", "F", "D", "H")
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    pads = list(f.Pads())
    if not f.GetReference().startswith("C") or len(pads) != 2:
        continue
    g = [p for p in pads if p.GetNetname() == gnd]
    s = [p for p in pads if p.GetNetname() and p.GetNetname() != gnd]
    if len(g) != 1 or len(s) != 1:
        continue
    net = s[0].GetNetname()
    targets = [(o.GetReference(), q) for o in b.GetFootprints() for q in o.Pads()
               if q.GetNetname() == net and not o.GetReference().rstrip("0123456789").startswith(PASSIVE)]
    if not targets:
        continue
    ref, pin = min(targets, key=lambda t: dist(t[1].GetPosition(), s[0].GetPosition()))
    layer = pcbnew.F_Cu if g[0].IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    n = piece_of(pieces, layer, g[0].GetPosition())
    part_gnd = [q for q in b.FindFootprintByReference(ref).Pads() if q.GetNetname() == gnd and q.IsOnLayer(layer)]
    shared = "n/a" if not part_gnd else ("yes" if n is not None and any(piece_of(pieces, layer, q.GetPosition()) == n for q in part_gnd) else "NO")
    near = min((dist(v.GetPosition(), g[0].GetPosition()) for v in gvias), default=float("nan"))
    print(f"  {f.GetReference():4} {f.GetValue():7} {dist(s[0].GetPosition(), pin.GetPosition()):4.1f} mm from {ref}-{pin.GetNumber()} ({net})"
          f" | shared ground {shared:3} | nearest ground via {near:.1f} mm")

# --- 7. vias touching or inside SMD pads ------------------------------------------------------
for v in vias(b):
    q = v.GetPosition()
    for f in b.GetFootprints():
        for p in f.Pads():
            # through-hole pads, and unnumbered pads (paste windows of an exposed pad) are not landing pads
            if p.HasHole() or not p.GetNumber():
                continue
            thermal = p.GetNetname() == v.GetNetname() and MM(p.GetSize(pcbnew.F_Cu).x) * MM(p.GetSize(pcbnew.F_Cu).y) > 4
            e = edge_dist(p, q)
            if e < 0.25 and not thermal:
                print(f"  via {'IN' if e == 0 else 'against'} pad {f.GetReference()}-{p.GetNumber()} {v.GetNetname()}"
                      f" ({MM(q.x):.2f}; {MM(q.y):.2f}) edge {e:.2f} mm")
shutil.rmtree(tmp, ignore_errors=True)
