---
name: board-check
description: "Full check of a KiCad board after a human save: DRC with schematic parity on a complete copy, what changed since the last check, ground islands, decoupling distances, vias in pads. Use when the human says \"check\", \"recheck\", \"done, check\", \"what changed\" while routing by hand."
argument-hint: "[board.kicad_pcb] [--prev older.kicad_pcb] [--gnd GND]"
---

# Board check

The script is shared with the main skill: `../kicad-pcb-helper/scripts/board_check.py`, relative to this
skill's base directory. Run it with KiCad's Python (on Windows `"C:/Program Files/KiCad/10.0/bin/python.exe"`), not the system Python. It only reads the board.

```
KPY <base>/../kicad-pcb-helper/scripts/board_check.py board.kicad_pcb [--prev older.kicad_pcb] [--gnd GND] [--no-snapshot]
```

## Steps

1. Find the board (`$ARGUMENTS`, or the `.kicad_pcb` of the project). Read its save time first: if it
   predates the request, ask the human to refill zones (**B**) and save (**Ctrl+S**); KiCad does not
   refill on save. If `~<name>.kicad_pcb.lck` exists, KiCad has it open: read only.
2. Run the script. It copies the board with its `.kicad_pro` and `.kicad_sch` (without them the zones
   refill wrong and parity is skipped silently) and compares with the snapshot of the previous run.
3. Report, shortest first: DRC errors / unconnected / parity (must be 0, 0, 0); what moved; per-net
   length and via changes; new ground islands; decoupling distances that got worse; vias in pads.
4. Give a verdict, then the few concrete fixes with coordinates. Do not re-list what did not change.
5. "What can I remove?": prove it on a scratch copy (remove, refill, DRC, compare ground pieces).

Rules and context behind this check: the main `kicad-pcb-helper` skill.
