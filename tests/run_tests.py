"""Runs every script on tests/fixture/demo.kicad_pcb and checks it finds the defects planted there.

    KPY tests/run_tests.py            (KPY = KiCad's Python, see the README)

The JLC test needs the network (EasyEDA footprint download) and is skipped without it.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skills" / "kicad-pcb-helper" / "scripts"
BOARD = HERE / "fixture" / "demo.kicad_pcb"
failed = 0


def run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), str(BOARD), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def expect(name, ok, out):
    global failed
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failed += 1
        print("\n".join("     " + line for line in out.splitlines()[-15:]))


rc, out = run("board_check.py", "--no-snapshot")
expect("board_check: DRC ran", "DRC " in out, out)
m = re.search(r"C1 .*?(\d+\.\d) mm from U1-1", out)
expect("board_check: C1 reported about 10 mm from U1-1", bool(m) and 9 < float(m.group(1)) < 13, out)
m = re.search(r"C2 .*?(\d+\.\d) mm from U1-1", out)
expect("board_check: C2 reported close to U1-1", bool(m) and float(m.group(1)) < 5, out)
expect("board_check: via inside U1-2 found", re.search(r"via IN pad U1-2", out) is not None, out)

rc, out = run("redundant_gnd_exits.py")
expect("redundant_gnd_exits: C2's exit found redundant", re.search(r"redundant .*? 1\b", out) is not None and "C2-2" in out, out)

rc, out = run("gnd_via_spots.py", "--net", "SIG")
m = re.search(r"(\d+) free spot", out)
expect("gnd_via_spots: free spots around the SIG via", bool(m) and int(m.group(1)) > 0, out)

with tempfile.TemporaryDirectory() as tmp:
    bom = Path(tmp) / "bom.csv"
    bom.write_text('Comment,Designator,Footprint,LCSC Part #\nTLV75733PDBV,U1,SOT-23-5,C485517\n', encoding="utf-8")
    cpl = Path(tmp) / "cpl.csv"
    rc, out = run("jlc_cpl.py", "--bom", str(bom), "-o", str(cpl))
    if "not fitted" in out and not (Path(tmp) / "easyeda" / "C485517.json").exists():
        print("SKIP jlc_cpl: EasyEDA not reachable")
    else:
        row = cpl.read_text(encoding="utf-8").splitlines()[1].split(",")
        # KiCad's SOT-23-5 at 0 degrees is EasyEDA's turned by 270 (see references/jlcpcb.md)
        expect("jlc_cpl: U1 fitted at 270 degrees", row[0] == "U1" and row[4] == "270", out)
        rc, out = run("jlc_cpl.py", "--bom", str(bom), "--check", str(cpl))
        expect("jlc_cpl --check: own output accepted", rc == 0, out)
        cpl.write_text(cpl.read_text(encoding="utf-8").replace(",270", ",180"), encoding="utf-8")
        rc, out = run("jlc_cpl.py", "--bom", str(bom), "--check", str(cpl))
        expect("jlc_cpl --check: 180 degrees (the community table) rejected", rc == 1 and "WRONG" in out, out)

print("all passed" if not failed else f"{failed} failed")
sys.exit(1 if failed else 0)
