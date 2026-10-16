# JLCPCB assembly files

## How JLC places a part

JLC looks up the LCSC part number of each BOM line, takes the EasyEDA footprint of that part, puts the
footprint's origin on the CPL point (Mid X, Mid Y, Y pointing up) and turns it counter-clockwise, seen
from the top, by the CPL rotation. The "Component Placements" preview draws exactly that.

KiCad's footprint for the same package usually differs in two ways:

- **origin**: KiCad connectors often have their origin on pin 1 or between rows; modules on the
  pad field; EasyEDA uses its own centre;
- **zero angle**: EasyEDA footprints of the same package are not drawn the same way by every maker.

Measured on one real order, for the same board, KiCad angle to JLC angle:

| Part (LCSC) | Package | Correct offset | Community table said |
|---|---|---|---|
| AO3401A (C15127), BAT54C (C37704) | SOT-23 | +180 | +180 |
| USBLC6-2SC6 (C7519), USBLC6-4SC6 (C111212) | SOT-23-6 | +270 | +180 |
| TLV75733PDBV (C485517) | SOT-23-5 | +270 | +180 |
| 2N7002W (C7420322) | SOT-323 | +180 | +180 |
| TP4056 (C16581) | ESOP-8 | +270 | +270 |
| RV-3032-C7 (C5127802) | 8-pin 3.2 × 1.5 | +270 | none |
| HRO TYPE-C-31-M-12 (C165948) | USB-C | 0 | +180 (connector facing inwards) |

And positions: the ESP32-S3-WROOM-1 (C2913202) EasyEDA origin sits 3.6 mm from the body centre KiCad's
Fab layer gives; JST GH/PH connectors 0.5 to 0.7 mm. A body-centre CPL looked plausible and was wrong.

## The fit

`scripts/jlc_cpl.py` downloads the EasyEDA footprint of each LCSC number:

    https://easyeda.com/api/products/<LCSC>/components?version=6.4.19.5

(`result.packageDetail.dataStr`: `head.x/y` is the origin, each `PAD~shape~x~y~w~h~layer~net~number~...`
is in units of 10 mil, Y pointing down). It matches pads by pin number, tries 0/90/180/270, keeps the
angle with the smallest spread, and the mean offset gives the position. Spread up to about 0.45 mm is
normal when the two footprints have pads of different lengths (SOIC/ESOP); a wrong angle gives 2 mm or
more. The server answers HTTP 403 to Python's urllib and to bursts of requests: the script uses curl
and keeps a cache.

## Preview checklist

- Each part on its pads; pin 1 or cathode on the right side; connector openings to the board edge;
  module antenna over the edge or the keep-out, not over copper.
- A part shown without a 3D model, or as a generic box, is placed by its footprint: check it with
  `jlc_cpl.py --check`, not by eye.
- Set "Confirm Parts Placement" and "Confirm Production file" to Yes: JLC's engineers send their own
  placement for approval before assembly.

## Parts

- Prefer parts in stock on LCSC; an "Extended" part costs a loading fee per order.
- An out-of-stock original replaced by a look-alike (for example a JST GH clone) often has no 3D model
  and no guarantee of mating with the original cable. A different pin count of an in-stock original
  can be the better fix, and different pin counts per connector also prevent swapped cables.
- After changing a part: update the BOM source, regenerate BOM and CPL, run `jlc_cpl.py --check`.
