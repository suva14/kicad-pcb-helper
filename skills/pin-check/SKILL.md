---
name: pin-check
description: "Pin-by-pin check of a KiCad board against the parts actually bought, before ordering. Use when asked to \"check the pinout\", \"pin check\", \"are the pins right\", \"will it work\" for a board with LCSC part numbers, or before a JLCPCB order. Lists each pad's net beside the pin name in the LCSC/EasyEDA symbol and flags ground, supply and NC contradictions."
argument-hint: "[board.kicad_pcb] [BOM.csv]"
---

# Pin check

DRC and schematic parity only prove that the board equals the schematic. A symbol with its pins in
the wrong order passes both. This compares every pad with the maker's pin name for the LCSC number.

The script is shared with the main skill: `../kicad-pcb-helper/scripts/pin_check.py`, relative to this
skill's base directory. Run it with KiCad's Python (on Windows
`"C:/Program Files/KiCad/10.0/bin/python.exe"`), not the system Python.

## Steps

1. Find the board and the BOM. Arguments, if given: `$ARGUMENTS`. Otherwise look for the
   `.kicad_pcb` in the project and a BOM CSV with a `Designator` and an `LCSC Part #` (or `LCSC`)
   column; without a BOM, the script reads an `LCSC` field on the footprints.
2. Run:
   ```
   KPY <base>/../kicad-pcb-helper/scripts/pin_check.py board.kicad_pcb --bom BOM.csv [--cache DIR] [--gnd GND]
   ```
   `--cache` defaults to `easyeda/` beside the BOM: reuse the folder `jlc_cpl.py` filled. The EasyEDA
   server refuses bursts (HTTP 403); the cache downloads each part once.
3. Read **every line**, not only the flagged ones. For each part, say whether the wiring makes sense:
   - transistors: G/S/D (or B/E/C) where the circuit needs them; P-MOSFET battery switch with drain on
     the battery and source on the system;
   - diodes: cathode on the right side; dual diodes (BAT54C/A/S) common pin;
   - regulators: IN, OUT, EN, and an enable pull-down if the regulator must be off by default;
   - chargers: TEMP, CE, PROG value against the cell;
   - MCU: no flash/PSRAM pins, strapping pins free or pulled correctly, USB D-/D+ on the right GPIO.
4. Parts listed as "symbol numbers its pins only" (connectors, ESD arrays, fuses): check against the
   datasheet. USBLC6-2SC6: 1/6 = I/O1, 2 = GND, 3/4 = I/O2, 5 = VBUS. USBLC6-4SC6: 1, 3, 4, 6 = I/O,
   2 = GND, 5 = VBUS.
5. Connectors the board cannot protect: battery JST-PH (red lead must face the `+` silkscreen; leads
   are not standardised), cables made to order. Say what to check at assembly.
6. Report: a table per part (OK / to check / wrong), then what this check cannot see (a wrong LCSC
   datasheet, a part substituted at assembly). Never write "verified" for a part checked only against
   the EasyEDA symbol: say "matches the LCSC symbol".
