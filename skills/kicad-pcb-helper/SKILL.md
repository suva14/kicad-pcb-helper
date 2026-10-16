---
name: kicad-pcb-helper
description: Use when placing, routing, reviewing or checking a KiCad PCB (KiCad 8 to 10), when a human routes by hand and asks Claude to check after each save ("check", "recheck", "what changed"), when deciding whether a board will work before ordering, or when preparing JLCPCB assembly files (BOM, CPL, "Component Placements" preview problems such as offset or rotated parts, missing 3D models).
---

# KiCad PCB helper

Methods and checks learned while a human reworked, by hand, a 2-layer board that Claude had placed and
routed first. Claude gives a complete, DRC-clean starting point fast; the human then removes what
Claude over-does and fixes what it under-weights. Follow the human methods below from the start, and
use the scripts to check every step. Numbers behind these rules: `references/ai-vs-human.md`.

## Ground rules

- **One version of the board on disk.** Trials go to a scratch folder, never beside the board as
  `board_v2.kicad_pcb`. Back up to scratch before any scripted edit.
- **Never write a board KiCad has open.** `~<name>.kicad_pcb.lck` beside it means the PCB editor is
  open: read it, do not save over it, ask the human to close the editor first.
- **Scripted edits stay small and announced.** Prefer telling the human what to change; when a script
  edits, remove only what is clearly obsolete and leave the routing to the human.
- **Never trust a check that ran on an incomplete copy.** A board copied without its `.kicad_pro`
  refills its zones with default clearances (wrong pour areas, false "lost ground"); a DRC run without
  the `.kicad_sch` beside the board skips schematic parity silently. `board_check.py` copies both.
- **KiCad's Python only.** Run the scripts with the Python shipped with KiCad (`pcbnew` module).
  On Windows from Git Bash, arguments starting with `/` are rewritten into paths: the scripts accept
  net names without the leading slash (`SPI_SCK` for `/SPI_SCK`).
- Some pcbnew calls raise a modal assert dialog in KiCad instead of an exception (for example
  `PCB_VIA.GetWidth()` without a layer: use `GetWidth(pcbnew.F_Cu)`). If a script hangs, tell the human
  the dialog comes from the script, not from their file.

## The check loop (human routes, Claude checks)

1. The human says "done, check". Read the file's save time first. If it predates the request, ask them
   to refill zones (**B**) and save (**Ctrl+S**); KiCad does not refill on save.
2. Run `scripts/board_check.py board.kicad_pcb`. It compares with the previous run on its own.
3. Report, shortest first: DRC errors / unconnected / parity (must be 0, 0, 0); what moved; per-net
   length and via changes; new ground islands; decoupling distances that got worse; vias in pads.
4. Give a verdict, then the few concrete fixes with coordinates. Do not re-list what did not change.
5. When asked "what can I remove", prove it: remove the item on a scratch copy, refill, DRC, compare
   ground pieces. A via is removable only if the pour stays in one piece and the DRC stays clean.

## Placement: what the human did better

- **Regulator next to its largest load** (the MCU/module), not grouped with the input connectors.
  Claude grouped "the power block" by function and left 78 mm and 2 vias between the 3.3 V regulator
  and the module. Place the load first, then the regulator beside it, then the charger and connectors.
- **Decoupling capacitor on the pin it serves**, its ground pad in the same pour piece as the IC's
  ground pin, without a via if possible. Claude placed capacitors where the router had room (6 to 16 mm).
- **Pull-ups along the line, at the connector** they serve, not in a neat row elsewhere.
- **Order parts by pin order** so lines do not cross: whole buses then route on one layer, no via.
- **Rotate small parts** (regulator, RTC, ESD arrays) so their pins face their neighbours; re-check the
  decoupling distances after each rotation.
- **Test points** spaced for a probe and labelled; on the back side when the top is crowded.

## Routing: what Claude over-does

- **Ground exit tracks.** One short track and via per ground pad, on top of two ground pours: 50 of 55
  were useless. An SMD pad inside a ground pour is already connected. `scripts/redundant_gnd_exits.py`
  lists them.
- **Blanket stitching.** A via grid every 5 mm, everywhere. Stitch where it matters: around USB,
  under and around RF modules, beside signal vias that change layers, at ESD ground pins.
- **Locked items.** Locking pre-routed tracks blocked the human's rework. Do not lock what a human
  will touch.
- **Leftovers.** Zero-length segments, dangling vias, vias inside or touching pads (solder wicking).
  Keep a via about 0.45 mm from the pad edge.

## Routing: what to keep doing

- Power on one layer and short, without vias, when the layout allows; widths sized for the current
  (about 1 mOhm per mm at 0.5 mm wide in 35 um copper; a 0.3 mm via carries about 1 A).
- Keep the reference plane continuous under signals. Tracks bundled on the ground layer cut slots in
  it; leave about 0.65 to 0.7 mm between two tracks for the pour to pass, or join the pieces with a via.
- Neck-down at fine-pitch pins (for example 0.187 mm at USB-C 0.5 mm pitch) is normal.
- USB full speed needs no length matching; keep the pair together, over unbroken ground.
- ESD protection ground pin: a ground via right at the pin.
- Island removal "always" on pours; check what each remaining small piece is tied to
  (a connector shield pad can be the only link, which is acceptable).

## "Will it work?" review before ordering

Parity 0 and DRC 0 only prove the board equals the schematic. Review the schematic itself:

1. **Pinout against the part actually bought**: compare each IC, transistor, diode and connector
   symbol, pin by pin, with the symbol or datasheet of the LCSC/manufacturer part number in the BOM.
   The EasyEDA files `jlc_cpl.py` caches in `easyeda/` beside the CPL carry each pin's name.
   Watch SOT-23 transistor pinouts, diode cathodes, MOSFET orientation in power paths.
2. **Every resistor: needed, and on the right side.** Series resistors at the driver end
   (MCU side for clocks and outputs); ESD arrays at the connector side of series resistors; LED
   resistors between cathode and driver; dividers and their filter capacitor at the ADC pin;
   pull-ups/pull-downs that hold gates, enables and chip selects during boot.
3. **What is missing**: CC resistors on USB-C sinks, EN RC on ESP32, SD card pull-ups (DAT1/DAT2 too),
   I2C pull-ups, battery protection (on board or in the cell), gate pull-downs.
4. **Firmware obligations** the schematic creates (internal pull-ups to enable, pins to drive at boot,
   hold lines), written down for whoever writes the firmware.
5. MCU pins: no flash/PSRAM pins (ESP32-S3 octal PSRAM: GPIO 33 to 37), no strapping pins trapped.

## JLCPCB assembly

- **Generate the CPL with `scripts/jlc_cpl.py`**, never with a per-package rotation table. JLC places
  the EasyEDA footprint of each LCSC part, origin on the CPL point, turned counter-clockwise by the CPL
  angle. Origins and zero angles differ from KiCad and between makers of the same package. A table
  copied from community tools turned 4 ICs by 90 degrees, reversed a USB-C connector and shifted a
  module by 3.6 mm on a real order. Details: `references/jlcpcb.md`.
- **Check any CPL** made elsewhere with `jlc_cpl.py --check`.
- **Missing 3D model in the preview is not a placement problem**: JLC places by footprint. Verify
  such a part numerically (the fit) instead of visually.
- **Order with "Confirm Parts Placement" and "Confirm Production file" set to Yes**: nothing is
  assembled before the human approves JLC's own rendering.
- **Prefer original connectors in stock** over look-alike clones without a model; check stock on
  LCSC before switching a part.
- Never pay, never create accounts, never submit an order: the human does it.

## Scripts

All in `scripts/`, read-only on the board unless stated, run with KiCad's Python (`KPY` below).

| Script | Use |
|---|---|
| `board_check.py board.kicad_pcb [--prev old] [--gnd NET]` | the check loop: DRC + parity on a full copy, totals, changes since last run, islands, decoupling, vias in pads |
| `jlc_cpl.py board --bom BOM.csv -o CPL.csv` | CPL fitted on JLC's footprints; `--check CPL.csv` to audit one |
| `gnd_via_spots.py board --net SPI_SCK` | free spots for a ground via near each via of a signal net |
| `redundant_gnd_exits.py board` | ground exit tracks a pour makes useless |

## With kicad-happy

This skill complements the [kicad-happy](https://github.com/aklofas/kicad-happy) plugin, where this
work started: use kicad-happy for the full design review (schematic and PCB analyzers, EMC, thermal,
gerbers, sourcing) and this skill for the hand-routing loop, the layout rules and the JLC placement.
Its EMC analyzer gives a score (100 minus penalties). Read its findings before chasing the number: its counting changes when unrelated nets change, and some rules are false
positives on small boards (decoupling distance to an ESD array, for example).
