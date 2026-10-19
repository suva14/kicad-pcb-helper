---
name: gnd-via-spots
description: "Free spots for a ground stitching via next to each via of a signal net (return path when a signal changes layers). Use when asked where to put a ground via beside a clock or fast signal via, or when an EMC check asks for a ground via near a signal via."
argument-hint: "[board.kicad_pcb] --net NET"
---

# Gnd via spots

The script is shared with the main skill: `../kicad-pcb-helper/scripts/gnd_via_spots.py`, relative to this
skill's base directory. Run it with KiCad's Python (on Windows `"C:/Program Files/KiCad/10.0/bin/python.exe"`), not the system Python. It only reads the board.

```
KPY <base>/../kicad-pcb-helper/scripts/gnd_via_spots.py board.kicad_pcb --net SPI_SCK [--rmin 0.75 --rmax 0.95] [--gnd GND]
```

## Steps

1. Find the board and the signal net (`$ARGUMENTS`). On Windows from Git Bash, give the net without
   its leading slash (`SPI_SCK`, not `/SPI_SCK`): Git Bash rewrites `/...` into a path.
2. Run the script. Each spot sits inside the filled ground pour on both outer layers and keeps the
   clearance from other nets.
3. Give the human one or two spots per signal via, with coordinates, inside the range rather than on
   its edge (EMC checkers often require strictly less than 1.0 mm).
4. After the human places the via: refill, save, then run a board check; pour clearances can differ
   from the script's.

Rules and context behind this check: the main `kicad-pcb-helper` skill.
