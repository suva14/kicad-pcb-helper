"""Pin-by-pin check of the board against the part actually bought: pad -> net on the board, beside
pad -> pin name in the LCSC/EasyEDA symbol of the part number in the BOM.

    KPY pin_check.py board.kicad_pcb --bom BOM.csv [--cache easyeda/] [--all]

DRC and schematic parity only prove that the board equals the schematic. A symbol whose pins are in
the wrong order (a SOT-23 transistor of another pinout, a regulator with IN and OUT swapped, a diode
cathode on the wrong pad) passes both and gives a board that does not work. The EasyEDA symbol of an
LCSC number carries the maker's pin names; this lists them beside the board's nets, pad by pad, and
flags the obvious contradictions:

  - a ground pin (GND, VSS, EP, PAD) on a net that is not ground,
  - a supply pin (VCC, VDD, VIN, IN, VBUS, 3V3...) on ground,
  - an NC pin wired to a net.

The rest needs a human eye: read every line of every IC, transistor and diode. Passives (R, C) and
parts whose symbol only numbers its pins (connectors, ESD arrays) are skipped unless --all; check
those against the datasheet. Same LCSC sources and cache as jlc_cpl.py.
"""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

import pcbnew

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("--bom", help="BOM CSV with Designator and LCSC columns")
ap.add_argument("--cache", help="folder of EasyEDA files (default: easyeda/ beside the BOM or the board)")
ap.add_argument("--gnd", default="GND", help="ground net name, without the leading slash")
ap.add_argument("--all", action="store_true", help="also list passives and parts without pin names")
a = ap.parse_args()
cache = Path(a.cache) if a.cache else Path(a.bom or a.board).resolve().parent / "easyeda"

GROUND = re.compile(r"^(GND|AGND|DGND|PGND|VSS|EP|PAD|EPAD|THERMAL)\d*$", re.I)
SUPPLY = re.compile(r"^(VCC|VDD|VDDA|VIN|IN|VBUS|VBAT|3V3|5V|VS|VDDIO|AVDD|DVDD)\d*$", re.I)
NC = re.compile(r"^(NC|N\.C\.|DNC)\d*$", re.I)


def pin_names(code):
    """{pin number: name} from the EasyEDA symbol of an LCSC number, downloaded once (cached)."""
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{code}.json"
    if not f.exists():
        url = f"https://easyeda.com/api/products/{code}/components?version=6.4.19.5"
        if subprocess.run(["curl", "-sf", "-m", "30", "-o", str(f), url]).returncode:
            f.unlink(missing_ok=True)
            return None
    r = json.loads(f.read_text(encoding="utf-8"))
    r = r.get("result", r)
    ds = r["dataStr"]
    ds = json.loads(ds) if isinstance(ds, str) else ds
    names = {}
    for s in ds.get("shape", []):
        if not s.startswith("P~"):
            continue
        parts = s.split("^^")       # P~show~type~number~x~y~... ^^ dot ^^ path ^^ name ^^ number ^^ ...
        number = parts[0].split("~")[3]
        name = parts[3].split("~")[4] if len(parts) > 3 and len(parts[3].split("~")) > 4 else ""
        names[number] = "" if name == number else name
    return names


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


def natural(fp):
    r = fp.GetReference()
    return re.sub(r"\d+", "", r), int(re.sub(r"\D", "", r) or 0)


flags = 0
for fp in sorted(board.GetFootprints(), key=natural):
    ref = fp.GetReference()
    if ref not in lcsc or (re.match(r"^(R|C|L|FB)\d", ref) and not a.all):
        continue
    names = pin_names(lcsc[ref])
    if names is None:
        print(f"\n{ref} {lcsc[ref]}: EasyEDA data not available, check against the datasheet")
        continue
    pads = sorted((p for p in fp.Pads() if p.GetNumber()), key=lambda p: (len(p.GetNumber()), p.GetNumber()))
    if not any(names.get(p.GetNumber()) for p in pads) and not a.all:
        print(f"\n{ref} {fp.GetValue()} {lcsc[ref]}: symbol numbers its pins only, check against the datasheet")
        continue
    print(f"\n{ref} {fp.GetValue()} {lcsc[ref]}")
    for p in pads:
        net = p.GetNetname().lstrip("/")
        name = names.get(p.GetNumber(), "")
        free = not net or net.startswith("unconnected-")
        note = ""
        if name and GROUND.match(name) and not free and net != a.gnd:
            note = "GROUND PIN NOT ON GROUND"
        elif name and SUPPLY.match(name) and net == a.gnd:
            note = "SUPPLY PIN ON GROUND"
        elif name and NC.match(name) and not free:
            note = "NC PIN WIRED"
        flags += bool(note)
        print(f"  {p.GetNumber():>4}  {name or '-':12} {net or '(free)':28} {note}")
print(f"\n{flags} contradiction(s) flagged; read every line above anyway")
raise SystemExit(1 if flags else 0)
