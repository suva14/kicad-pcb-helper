# Claude's layout against the human rework

The board: 60 × 40 mm, 2 layers, ESP32-S3 module, LiPo charger, 3.3 V LDO, RTC, microSD, USB-C,
three JST-GH connectors; about 70 parts. Claude generated the schematic, the placement and a fully
routed, DRC-clean board (autorouter plus scripted fixes). The human then reworked it in KiCad over
roughly a day, asking Claude to check after each save.

| | Claude's board | After the human rework |
|---|---|---|
| Vias | 166 | 98 |
| Ground vias | 77 | 29 |
| Ground exit tracks (pad to via) | 55, of which 50 useless | 0 |
| Track length | 1601 mm | 1288 mm |
| 100 nF decoupling, capacitor to pin | 6 to 16 mm | 1.7 to 3.3 mm |
| 3.3 V regulator to the module | 78 mm, 2 vias | unchanged (no room to move it late) |
| Locked items | 77 | 0 needed |
| kicad-happy EMC score | 46 | 61 to 70 |
| DRC errors / unconnected / parity | 0 / 0 / 0 | 0 / 0 / 0 |

## What Claude over-did

- A track and via from every ground pad, on top of two full ground pours.
- A stitching grid every 5 mm, placed without regard to where return currents flow.
- Decoupling capacitors placed where the router had room, not on their pin.
- Pull-ups aligned in a row away from the connector they serve.
- Every pre-routed connection locked, which the human had to unlock one by one.
- Zero-length segments, a via inside a pad.
- The regulator grouped with the power input "block", far from its load; complete routing was
  prioritised over "regulator next to its largest load". Too late to move once everything else was
  placed around it.

## What the human did

- Capacitor on the pin, its ground in the same pour piece as the IC's ground, no via.
- Pull-ups along the line, at the connector.
- Parts ordered by pin order: crossings vanish, buses route on one layer (two SD lines lost their vias).
- Shorter tracks everywhere, power routed on one layer without vias.
- Tracks moved apart so the ground pour flows between them instead of leaving slots.
- Small parts rotated so their pins face their neighbours, then decoupling re-checked.
- Test points spaced and moved to the back side.

## What Claude brought

- The complete starting point in hours: schematic with sourcing numbers, placement in the outline,
  100 % routing with DRC and parity clean, differential USB pair, 3D models, manufacturing files.
- A check after every human pass. It caught: a 0.125 mm clearance, vias in pads, zones not refilled
  before saving, a lost ground via on the USB ESD array, a ground pour split in two, a disconnected
  I2C line after a rotation.
- Proof before removal: a via is removable when a scratch copy without it refills in one piece and
  passes DRC.
- The JLC placement check that found 8 misplaced parts in a file generated with community rotation
  tables (see `jlcpcb.md`).

## Lesson for the next board

Start with the human methods: load first, regulator beside it; capacitors on pins; pull-ups at
connectors; order by pins; no ground exits; stitching only where useful; nothing locked. Then let the
human refine, and check after every save.
