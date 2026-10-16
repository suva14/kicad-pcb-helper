"""Builds tests/fixture/demo.kicad_pcb: a tiny board with one known defect of each kind the scripts look for.

    KPY tests/make_fixture.py

30 x 20 mm, two ground pours. Contents:
  U1  SOT-23-5 on VCC (pin 1) and GND (pin 2), the "IC"
  C1  0402 on VCC/GND, 10 mm from U1     -> decoupling too far
  C2  0402 on VCC/GND, beside U1, with a ground exit track and via -> redundant ground exit
  a ground via inside U1's pad 2           -> via in pad
  a via on SIG with free copper around it  -> spots for a ground stitching via
"""
import os
import sys
from pathlib import Path

import pcbnew

OUT = Path(__file__).resolve().parent / "fixture" / "demo.kicad_pcb"
MM = pcbnew.FromMM


def pt(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def footprint_dirs():
    for var in ("KICAD10_FOOTPRINT_DIR", "KICAD9_FOOTPRINT_DIR", "KICAD8_FOOTPRINT_DIR"):
        if os.environ.get(var):
            yield Path(os.environ[var])
    exe = Path(sys.executable).resolve()
    for base in (exe.parent.parent / "share" / "kicad" / "footprints", Path("/usr/share/kicad/footprints"),
                 Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")):
        yield base


def load_fp(lib, name):
    for d in footprint_dirs():
        if (d / f"{lib}.pretty" / f"{name}.kicad_mod").exists():
            fp = pcbnew.FootprintLoad(str(d / f"{lib}.pretty"), name)
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            return fp
    raise SystemExit(f"footprint {lib}:{name} not found: set KICAD10_FOOTPRINT_DIR")


b = pcbnew.BOARD()
nets = {}
for n in ("GND", "VCC", "SIG"):
    nets[n] = pcbnew.NETINFO_ITEM(b, n)
    b.Add(nets[n])

corners = [(0, 0), (30, 0), (30, 20), (0, 20)]
for (x1, y1), (x2, y2) in zip(corners, corners[1:] + corners[:1]):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(x1, y1))
    s.SetEnd(pt(x2, y2))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    b.Add(s)


def place(ref, lib, name, x, y, pads, deg=0):
    fp = load_fp(lib, name)
    fp.SetReference(ref)
    fp.SetPosition(pt(x, y))
    fp.SetOrientationDegrees(deg)
    for p in fp.Pads():
        if p.GetNumber() in pads:
            p.SetNet(nets[pads[p.GetNumber()]])
    b.Add(fp)
    return fp


u1 = place("U1", "Package_TO_SOT_SMD", "SOT-23-5", 8, 10, {"1": "VCC", "2": "GND"})
place("C1", "Capacitor_SMD", "C_0402_1005Metric", 20, 10, {"1": "VCC", "2": "GND"})
c2 = place("C2", "Capacitor_SMD", "C_0402_1005Metric", 8, 6.5, {"1": "VCC", "2": "GND"})


def track(a, z, net, layer=pcbnew.F_Cu, w=0.25):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(a)
    t.SetEnd(z)
    t.SetWidth(MM(w))
    t.SetLayer(layer)
    t.SetNet(nets[net])
    b.Add(t)


def via(p, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(p)
    v.SetWidth(MM(0.6))
    v.SetDrill(MM(0.3))
    v.SetNet(nets[net])
    b.Add(v)


# ground exit: C2's ground pad -> short track -> via
g = next(p for p in c2.Pads() if p.GetNumber() == "2").GetPosition()
track(g, pcbnew.VECTOR2I(g.x + MM(1.2), g.y), "GND")
via(pcbnew.VECTOR2I(g.x + MM(1.2), g.y), "GND")
# via inside U1's ground pad
via(next(p for p in u1.Pads() if p.GetNumber() == "2").GetPosition(), "GND")
# a signal changing layers in the open
track(pt(14, 16), pt(18, 16), "SIG")
via(pt(18, 16), "SIG")
track(pt(18, 16), pt(24, 16), "SIG", pcbnew.B_Cu)

for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(nets["GND"])
    z.SetLocalClearance(MM(0.2))
    z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    o = z.Outline()
    o.NewOutline()
    for x, y in ((0.5, 0.5), (29.5, 0.5), (29.5, 19.5), (0.5, 19.5)):
        o.Append(MM(x), MM(y))
    b.Add(z)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
OUT.parent.mkdir(exist_ok=True)
b.Save(str(OUT))
print("written", OUT)
