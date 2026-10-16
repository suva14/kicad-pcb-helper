"""Shared helpers for the kicad-pcb-helper scripts. Run every script with KiCad's own Python,
which ships the `pcbnew` module:

    Windows : "C:/Program Files/KiCad/10.0/bin/python.exe" script.py ...
    macOS   : /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
    Linux   : python3 (with the distribution's kicad package installed)

Set KICAD_CLI if kicad-cli is not found next to that Python or on the PATH.
"""
import math
import os
import shutil
import sys
from pathlib import Path

import pcbnew

MM = pcbnew.ToMM
FROM_MM = pcbnew.FromMM


def kicad_cli():
    """Path to kicad-cli: $KICAD_CLI, then next to this Python, then the PATH."""
    if os.environ.get("KICAD_CLI"):
        return os.environ["KICAD_CLI"]
    here = Path(sys.executable).parent
    for name in ("kicad-cli.exe", "kicad-cli"):
        if (here / name).exists():
            return str(here / name)
    found = shutil.which("kicad-cli")
    if not found:
        raise SystemExit("kicad-cli not found: set KICAD_CLI")
    return found


def lock_file(board):
    """KiCad writes ~<name>.kicad_pcb.lck while the PCB editor has the board open."""
    p = Path(board)
    lck = p.with_name(f"~{p.name}.lck")
    return lck if lck.exists() else None


def load(board, fill=True):
    b = pcbnew.LoadBoard(str(board))
    if fill:
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return b


def tracks(b):
    return [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA"]


def vias(b):
    return [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]


def dist(a, c):
    return MM(int(math.hypot(a.x - c.x, a.y - c.y)))


def edge_dist(pad, q):
    """Distance in mm from point q to the bounding box of a pad (0 inside)."""
    bb = pad.GetBoundingBox()
    dx = max(bb.GetLeft() - q.x, 0, q.x - bb.GetRight())
    dy = max(bb.GetTop() - q.y, 0, q.y - bb.GetBottom())
    return MM(int(math.hypot(dx, dy)))


def gnd_zones(b, gnd):
    """{layer: zone} for the copper pours of the ground net."""
    out = {}
    for z in b.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() == gnd:
            for layer in z.GetLayerSet().Seq():
                out[layer] = z
    return out


def fill_pieces(b, gnd):
    """[(layer, outline)] : every separate piece of filled ground copper."""
    out = []
    for layer, z in gnd_zones(b, gnd).items():
        polys = z.GetFilledPolysList(layer)
        out += [(layer, polys.Outline(n)) for n in range(polys.OutlineCount())]
    return out


def piece_of(pieces, layer, q):
    return next((n for n, (l, o) in enumerate(pieces) if l == layer and o.PointInside(q)), None)


def area_mm2(outline):
    return outline.Area() / 1e12


def net_name(b, name):
    """The board's net matching `name`, given with or without its sheet prefix ("SPI_SCK" or
    "/SPI_SCK"). Git Bash rewrites an argument starting with "/" into a Windows path
    ("C:/Program Files/Git/SPI_SCK"): only the last part of such a path is kept."""
    nets = set(b.GetNetsByName().keys()) if hasattr(b, "GetNetsByName") else {n.GetNetname() for n in b.GetNetInfo().NetsByName().values()}
    nets = {str(n) for n in nets}
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    for cand in (name, "/" + base, base):
        if cand in nets:
            return cand
    raise SystemExit(f"net {name!r} not on the board")


def guess_gnd(b):
    """The ground net: the net of the largest copper pour, else the most common pad net named *GND*."""
    zones = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()]
    if zones:
        return max(zones, key=lambda z: z.GetBoundingBox().GetArea()).GetNetname()
    names = [p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if "GND" in p.GetNetname().upper()]
    return max(set(names), key=names.count) if names else "GND"
