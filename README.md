# kicad-pcb-helper

A [Claude Code](https://claude.com/claude-code) plugin for designing KiCad boards with a human in the
loop: the human places and routes by hand, Claude checks the board after every save, reviews it before
ordering, and prepares JLCPCB assembly files that land on the right pads.

It comes from the design of a small battery-powered data logger (ESP32-S3, 60 × 40 mm, 2 layers) that
measures vibration on a bicycle for rolling-resistance studies. Claude produced the first complete,
DRC-clean board; a human then reworked it by hand. The rules in this skill are what that rework
taught: 166 vias down to 98, decoupling capacitors from 6 to 16 mm away down to 2 mm, no useless ground
tracks, and a JLC placement file that had silently rotated four ICs.

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

## Requirements

- KiCad 8 or later (developed on KiCad 10, Windows). The scripts run with **KiCad's own Python**,
  which provides the `pcbnew` module, and call `kicad-cli` (found next to that Python, on the PATH, or
  through `KICAD_CLI`).
- `curl` on the PATH for the JLC placement scripts (downloads EasyEDA footprints).
- Optional: the kicad-happy Claude Code plugin, for EMC scoring.

## Scripts

Run them yourself too: on Windows, `"C:/Program Files/KiCad/10.0/bin/python.exe" script.py ...`.

| Script | Purpose |
|---|---|
| `board_check.py board.kicad_pcb` | full check, compared with the previous run |
| `jlc_cpl.py board.kicad_pcb --bom BOM.csv -o CPL.csv` | JLCPCB placement file fitted on JLC's footprints |
| `jlc_cpl.py board.kicad_pcb --bom BOM.csv --check CPL.csv` | audit an existing placement file |
| `gnd_via_spots.py board.kicad_pcb --net SPI_SCK` | free spots for a ground via next to a signal's vias |
| `redundant_gnd_exits.py board.kicad_pcb` | ground exit tracks a solid pour makes useless |

All scripts only read the board. They live in `skills/kicad-pcb-helper/scripts/`.

## Layout

```
.claude-plugin/          plugin and marketplace manifests
skills/kicad-pcb-helper/
  SKILL.md               the method: ground rules, check loop, placement, routing, review, JLC
  references/            the measured AI-versus-human rework, JLC placement details
  scripts/               the checks
```

## License

MIT
