---
name: jlc-cpl
description: "JLCPCB placement file (CPL) fitted part by part on JLC's own EasyEDA footprints, or audit of an existing CPL. Use when preparing JLCPCB assembly files, or when JLC's \"Component Placements\" preview shows offset or rotated parts."
argument-hint: "[board.kicad_pcb] [BOM.csv] [-o CPL.csv | --check CPL.csv]"
---

# Jlc cpl

The script is shared with the main skill: `../kicad-pcb-helper/scripts/jlc_cpl.py`, relative to this
skill's base directory. Run it with KiCad's Python (on Windows `"C:/Program Files/KiCad/10.0/bin/python.exe"`), not the system Python. It only reads the board.

```
KPY <base>/../kicad-pcb-helper/scripts/jlc_cpl.py board.kicad_pcb --bom BOM.csv -o CPL.csv
   KPY <base>/../kicad-pcb-helper/scripts/jlc_cpl.py board.kicad_pcb --bom BOM.csv --check CPL.csv
```

## Steps

1. Find the board and the BOM (`$ARGUMENTS`, or in the project): the BOM needs `Designator` and
   `LCSC Part #` (or `LCSC`) columns, or the footprints an `LCSC` field.
2. Write the CPL with `-o`, or audit one made elsewhere with `--check`. Never use a per-package
   rotation table: origins and zero angles differ between makers of the same package.
3. The script downloads each part's EasyEDA footprint once (cache `easyeda/` beside the output; the
   server refuses bursts with HTTP 403) and fits it on the board's pads by pin number.
4. Report every WARNING / WRONG line: those parts must be checked in JLC's preview. A missing 3D model
   in the preview is not a placement problem: JLC places by footprint.
5. Remind the human to order with "Confirm Parts Placement" and "Confirm Production file" set to Yes.
   Never pay, create an account or submit an order.

Rules and context behind this check: the main `kicad-pcb-helper` skill.
