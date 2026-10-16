"""Free spots for a ground stitching via next to each via of a signal net, read-only.

    KPY gnd_via_spots.py board.kicad_pcb --net /SPI_SCK [--rmin 0.75 --rmax 1.0] [--gnd /GND]

A signal changing layers needs its return current to change layers too, close by. This lists, for each
via of --net, points between --rmin and --rmax mm from it where a via of the board's usual ground via
size (or --size/--drill) would:
  - sit fully inside the FILLED ground pour on both outer layers (so it actually connects), and
  - keep --clearance mm from every copper item of another net.
Verify the chosen spot with a DRC after placing it: pour clearances can differ from --clearance.
EMC checkers often require strictly less than 1.0 mm: aim inside the range, not on its edge.
"""
import argparse
import math

import pcbnew

from kicad_common import FROM_MM, MM, gnd_zones, guess_gnd, load, net_name, vias

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("--net", required=True, help="signal net, e.g. /SPI_SCK")
ap.add_argument("--gnd")
ap.add_argument("--rmin", type=float, default=0.75)
ap.add_argument("--rmax", type=float, default=0.95)
ap.add_argument("--clearance", type=float, default=0.2)
ap.add_argument("--size", type=float, help="via pad diameter, mm (default: the board's ground vias)")
a = ap.parse_args()

b = load(a.board)
gnd = net_name(b, a.gnd) if a.gnd else guess_gnd(b)
net = net_name(b, a.net)
gv = [v for v in vias(b) if v.GetNetname() == gnd]
size = FROM_MM(a.size) if a.size else (gv[0].GetWidth(pcbnew.F_Cu) if gv else FROM_MM(0.6))
zones = gnd_zones(b, gnd)
layers = [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if l in zones]
others = []
for t in b.GetTracks():
    if t.GetNetname() != gnd:
        others += [(l, t.GetEffectiveShape(l)) for l in layers if t.IsOnLayer(l)]
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() != gnd:
            others += [(l, p.GetEffectiveShape(l)) for l in layers if p.IsOnLayer(l)]


def free(q):
    for l in layers:
        filled = zones[l].GetFilledPolysList(l)
        for k in range(8):
            edge = pcbnew.VECTOR2I(q.x + int(size / 2 * math.cos(k * math.pi / 4)), q.y + int(size / 2 * math.sin(k * math.pi / 4)))
            if not filled.Contains(edge):
                return False
        if any(lay == l and s.Collide(q, size // 2 + FROM_MM(a.clearance)) for lay, s in others):
            return False
    return True


steps = max(2, int(round((a.rmax - a.rmin) / 0.05)) + 1)
for v in vias(b):
    if v.GetNetname() != net:
        continue
    c = v.GetPosition()
    near = min((MM(int(math.hypot(g.GetPosition().x - c.x, g.GetPosition().y - c.y))) for g in gv), default=float("nan"))
    spots = []
    for i in range(steps):
        r = a.rmin + i * (a.rmax - a.rmin) / (steps - 1)
        for deg in range(0, 360, 15):
            q = pcbnew.VECTOR2I(c.x + FROM_MM(r * math.cos(math.radians(deg))), c.y + FROM_MM(r * math.sin(math.radians(deg))))
            if free(q):
                spots.append((round(r, 2), round(MM(q.x), 2), round(MM(q.y), 2)))
    print(f"via {net} at ({MM(c.x):.2f}; {MM(c.y):.2f}), nearest {gnd} via {near:.2f} mm: {len(spots)} free spot(s)")
    for r, x, y in spots[:8]:
        print(f"   ({x:.2f}; {y:.2f})  {r:.2f} mm away")
