"""Ground "exits" that a solid pour makes useless, read-only.

    KPY redundant_gnd_exits.py board.kicad_pcb [--gnd /GND]

An exit is a short ground track from an SMD ground pad to a ground via. Autorouters and AI layouts add
one per pad; a human removes most of them, because an SMD pad inside a ground pour already connects to
it solidly. This lists every exit whose pad still sits in the main ground piece of its layer once the
exit's via is ignored, with the distance to the next ground via. Remove those exits in KiCad, refill
(B), save, and run board_check.py: the DRC must stay clean.
"""
import argparse
import math

import pcbnew

from kicad_common import FROM_MM, MM, area_mm2, fill_pieces, guess_gnd, load, net_name, tracks, vias

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("--gnd")
ap.add_argument("--max-len", type=float, default=2.5, help="longest track counted as an exit, mm")
a = ap.parse_args()

b = load(a.board)
gnd = net_name(b, a.gnd) if a.gnd else guess_gnd(b)
pieces = fill_pieces(b, gnd)
gv = [v for v in vias(b) if v.GetNetname() == gnd]
gt = [t for t in tracks(b) if t.GetNetname() == gnd]
th = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == gnd and p.HasHole()]


def piece(layer, q):
    return next((n for n, (l, o) in enumerate(pieces) if l == layer and o.PointInside(q)), None)


def main_piece(skip):
    """Union of pour pieces linked by vias (except `skip`), tracks and through-hole pads; return the
    function giving each piece's group, and the group with the largest area."""
    parent = list(range(len(pieces)))

    def root(n):
        while parent[n] != n:
            n = parent[n]
        return n

    def join(x, y):
        if x is not None and y is not None:
            parent[root(x)] = root(y)

    for v in gv:
        if v is not skip:
            join(piece(pcbnew.F_Cu, v.GetPosition()), piece(pcbnew.B_Cu, v.GetPosition()))
    for t in gt:
        join(piece(t.GetLayer(), t.GetStart()), piece(t.GetLayer(), t.GetEnd()))
    for p in th:
        join(piece(pcbnew.F_Cu, p.GetPosition()), piece(pcbnew.B_Cu, p.GetPosition()))
    area = {}
    for n, (_, o) in enumerate(pieces):
        area[root(n)] = area.get(root(n), 0) + area_mm2(o)
    return root, max(area, key=area.get)


pads = [(f.GetReference(), p) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == gnd and not p.HasHole()]
exits = []
for t in gt:
    if MM(t.GetLength()) > a.max_len:
        continue
    for ref, p in pads:
        for end, other in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
            if p.GetBoundingBox().Contains(end):
                v = next((v for v in gv if math.hypot(v.GetPosition().x - other.x, v.GetPosition().y - other.y) < FROM_MM(0.05)), None)
                if v is not None:
                    exits.append((f"{ref}-{p.GetNumber()}", p, v))
useless = []
for name, p, v in exits:
    root, main = main_piece(skip=v)
    layer = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    n = piece(layer, p.GetPosition())
    if n is not None and root(n) == main:
        nxt = min((MM(int(math.hypot(w.GetPosition().x - p.GetPosition().x, w.GetPosition().y - p.GetPosition().y))) for w in gv if w is not v),
                  default=float("nan"))
        useless.append((name, MM(v.GetPosition().x), MM(v.GetPosition().y), nxt))
print(f"{gnd} vias {len(gv)} | exits {len(exits)} | redundant (pad already in the main pour) {len(useless)}")
for name, x, y, nxt in sorted(useless):
    print(f"   {name:8} exit via at ({x:.2f}; {y:.2f}), next {gnd} via {nxt:.1f} mm from the pad")
