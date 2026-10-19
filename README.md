# kicad-pcb-helper

My notebook of lessons from designing KiCad boards with [Claude Code](https://claude.com/claude-code),
kept as a skill so the next project starts where the last one ended. It works alongside
[kicad-happy](https://github.com/aklofas/kicad-happy), which does the heavy design analysis; this
plugin adds what the hand rework of one real board taught: how a human places and routes, the check to
run after every save, the review before ordering, and JLCPCB placement files that land on the right pads.

## Origin

Everything started with **[kicad-happy](https://github.com/aklofas/kicad-happy)** by aklofas, a Claude
Code plugin that parses KiCad schematics and layouts, runs EMC pre-compliance, checks gerbers and
prepares boards for fabrication. It reviewed the design of a small battery-powered data logger
(ESP32-S3, 60 × 40 mm, 2 layers) that measures vibration on a bicycle for rolling-resistance studies.

On that project, Claude produced the first complete, DRC-clean board; I then reworked it by hand,
asking Claude to check after every save. The rework took the board from 166 vias to 98, brought
decoupling capacitors from 6 to 16 mm away down to about 2 mm, removed 50 useless ground tracks, and
exposed a JLC placement file that had silently rotated four ICs. This repository keeps those lessons and
the scripts written along the way, for my next boards and for anyone who finds them useful. The
measured comparison is in [`references/ai-vs-human.md`](skills/kicad-pcb-helper/references/ai-vs-human.md).

## What it does

- **Check after each save**: DRC with schematic parity on a complete copy of the project, what moved,
  per-net length and via changes, ground pour pieces and islands, decoupling distances, vias in pads.
- **Human layout methods from the start**: regulator beside its load, capacitor on its pin, pull-ups at
  the connector, parts in pin order, no ground exit tracks, stitching only where it matters.
- **"Will it work?" review**: pinout of every active part against the part actually bought, the role
  and side of every resistor, what is missing, the obligations the schematic puts on the firmware.
- **JLCPCB CPL fitted on JLC's footprints**: each part's EasyEDA footprint is downloaded and laid on
  the board's pads, pin by pin, to find the true position and rotation. A checker audits any CPL.

## Install

In Claude Code:

```
/plugin marketplace add suva14/kicad-pcb-helper
/plugin install kicad-pcb-helper@kicad-pcb-helper
```

The skill loads itself when you work on a KiCad board ("check my board", "recheck", "prepare the JLC
files", "the part is offset in the Component Placements preview"...).

## Examples

Real outputs from the project above, shortened; the first one combines two successive checks.

**"I rerouted and moved a few parts, check."** The human saves; the skill reads the save time, runs
the check, and reports only what matters:

```
saved 2026-10-16 17:15:06
DRC {('warning', 'silk_edge_clearance'): 2, ...} | unconnected 0 | parity 0
now: vias 98 (/GND 29) | tracks 1288 mm | near-zero segments 1 | /GND pour pieces (mm2) {'F.Cu': [1588, 28], 'B.Cu': [1856]}
  near-zero segment /EN B.Cu (110.24; 110.26)
  moved TP6   (114.00; 113.00 r0) -> (123.00; 106.00 r0)  flipped
  /TXD0          18.9 -> 7.0 mm, vias 1 -> 1
  C15  100nF    1.8 mm from U5-2 (/+3V3) | shared ground yes | nearest ground via 3.0 mm
```

**"The ESP32 is offset in JLC's Component Placements preview."** The placement file had been made with
a community rotation table. `jlc_cpl.py --check` lays JLC's own footprint of each part on the board:

```
J1    C165948    shift 6.52 mm, spread 3.50 mm WRONG  -> should be 154.229 -113.500 rot 90
U1    C7519      shift 0.00 mm, spread 2.11 mm WRONG  -> should be 152.800 -121.600 rot 270
U5    C2913202   shift 3.63 mm, spread 0.02 mm WRONG  -> should be 121.000 -110.377 rot 0
...
11 part(s) misplaced
```

A USB-C connector facing inwards, ESD arrays, the regulator and the RTC turned by 90 degrees, the module
3.6 mm off: all fixed before the order, by regenerating the file with `jlc_cpl.py`.

**"Which ground tracks can I delete?"** On the AI-routed board:

```
/GND vias 77 | exits 55 | redundant (pad already in the main pour) 50
   C10-2    exit via at (118.50; 131.59), next /GND via 2.5 mm from the pad
   ...
```

## Limitations

- Two-layer boards are what it was built and tested on. Four-layer boards work for the checks, but the
  ground-pour logic only looks at the outer layers.
- The CPL fit needs the LCSC part number of each part and the EasyEDA footprint behind it; parts with
  no common pin numbers between the two footprints are reported, not fitted. Top side only.
- EasyEDA's API is unofficial and rate-limited; the scripts cache what they download.
- The review checklist guides Claude; it does not replace reading the datasheets of the parts you buy.
- It never orders, pays, or submits anything: the human stays in charge of the manufacturer's site.

## Requirements

- KiCad 8 or later (developed on KiCad 10, Windows). The scripts run with **KiCad's own Python**,
  which provides the `pcbnew` module, and call `kicad-cli` (found next to that Python, on the PATH, or
  through `KICAD_CLI`).
- `curl` on the PATH for the JLC placement scripts (downloads EasyEDA footprints).
- Recommended: [kicad-happy](https://github.com/aklofas/kicad-happy), for schematic and layout analysis,
  EMC scoring and gerber checks. This plugin complements it and does not replace it.

## Scripts

Run them yourself too: on Windows, `"C:/Program Files/KiCad/10.0/bin/python.exe" script.py ...`.

| Script | Purpose |
|---|---|
| `board_check.py board.kicad_pcb` | full check, compared with the previous run |
| `jlc_cpl.py board.kicad_pcb --bom BOM.csv -o CPL.csv` | JLCPCB placement file fitted on JLC's footprints |
| `jlc_cpl.py board.kicad_pcb --bom BOM.csv --check CPL.csv` | audit an existing placement file |
| `pin_check.py board.kicad_pcb --bom BOM.csv` | each pad's net beside the pin name of the part actually bought |
| `gnd_via_spots.py board.kicad_pcb --net SPI_SCK` | free spots for a ground via next to a signal's vias |
| `redundant_gnd_exits.py board.kicad_pcb` | ground exit tracks a solid pour makes useless |

All scripts only read the board. They live in `skills/kicad-pcb-helper/scripts/`.

Each script also has its own command in Claude Code, which runs it and reads the result:

| Command | Runs |
|---|---|
| `/kicad-pcb-helper:board-check` | `board_check.py` |
| `/kicad-pcb-helper:pin-check` | `pin_check.py` |
| `/kicad-pcb-helper:jlc-cpl` | `jlc_cpl.py` |
| `/kicad-pcb-helper:gnd-via-spots` | `gnd_via_spots.py` |
| `/kicad-pcb-helper:redundant-gnd-exits` | `redundant_gnd_exits.py` |

`/kicad-pcb-helper:kicad-pcb-helper` loads the whole method (rules, review, JLC).

## Tests

`tests/fixture/demo.kicad_pcb` is a 30 × 20 mm board built by `tests/make_fixture.py` with one planted
defect per check (a far decoupling capacitor, a via in a pad, a redundant ground exit, a signal via
without stitching, a SOT-23-5 that a fixed rotation table gets wrong). Run:

```
"C:/Program Files/KiCad/10.0/bin/python.exe" tests/run_tests.py
```

The JLC test downloads one EasyEDA footprint and is skipped offline.

## Layout

```
.claude-plugin/          plugin and marketplace manifests
skills/kicad-pcb-helper/
  SKILL.md               the method: ground rules, check loop, placement, routing, review, JLC
  references/            the measured AI-versus-human rework, JLC placement details
  scripts/               the checks
tests/                   demo board with planted defects, and the test runner
```

## License

MIT: use it, fork it, adapt it to your own boards; keep the copyright notice.
