---
name: redundant-gnd-exits
description: "Lists ground exit tracks (short track from an SMD ground pad to a ground via) that a solid ground pour makes useless. Use when cleaning up an autorouted or AI-routed board, or when asked which ground tracks or vias can go."
argument-hint: "[board.kicad_pcb] [--gnd GND]"
---

# Redundant gnd exits

The script is shared with the main skill: `../kicad-pcb-helper/scripts/redundant_gnd_exits.py`, relative to this
skill's base directory. Run it with KiCad's Python (on Windows `"C:/Program Files/KiCad/10.0/bin/python.exe"`), not the system Python. It only reads the board.

```
KPY <base>/../kicad-pcb-helper/scripts/redundant_gnd_exits.py board.kicad_pcb [--gnd GND] [--max-len 2.5]
```

## Steps

1. Find the board (`$ARGUMENTS`, or the project's `.kicad_pcb`). Read only: never write a board KiCad
   has open.
2. Run the script. Each listed exit has its pad still in the main ground piece of its layer once the
   exit's via is ignored.
3. Give the list to the human to remove in KiCad (prefer telling over scripting the removal), then:
   refill (**B**), save, and run a board check. The DRC must stay clean and the pour in one piece.

Rules and context behind this check: the main `kicad-pcb-helper` skill.
