# SNAP Mini Power Controller

Minimal solar charger and power distribution board, sized to power a mini handheld LoRa mesh node. It has solder pads for a 5 V solar panel, a 1S Li-ion battery, a load, an external switch that breaks the positive wire to the load, and an optional battery thermistor. A CN3163 charges the battery from the panel at up to 1 A, like the SD05CRMA module, with the same two status LEDs: red while charging, green when the battery is full. The LEDs are off until you bridge a solder jumper. A P-channel MOSFET protects everything from a battery connected backwards. 14.4 × 12.2 mm, no mounting holes: stick it down with foam tape or hot glue.

![Top](docs/images/pcb-top.png)

| Pads | Where | |
|---|---|---|
| **NTC** | top row, left | optional 10 kΩ battery thermistor (non-polar) |
| **−OUT+** | top row, middle | load − and + (switched) |
| **SW** | top row, right | the two switch wires (non-polar) |
| **+SOL−** | bottom row, left | solar panel + and − |
| **+BAT−** | bottom row, right | battery + and − |

The charger feeds the battery directly, so the battery keeps charging with the switch off; the switch only cuts the load. All the − pads are connected.

**Status LEDs (JP1):** JP1 is the pair of tiny pads in the top-right corner of the parts area, right of the LEDs' resistors. It's open as delivered, so the LEDs are off and draw nothing. Bridge it with a blob of solder to turn them on; they then take about 2–3 mA from the panel while charging.

**Battery thermistor (JP2):** charging works without a thermistor: JP2, the tiny pad pair just left of the IC's top-left pin, is closed by a copper link and switches temperature sensing off. To use one, solder a 10 kΩ B3950 NTC (taped to the cell) on the NTC pads and cut JP2's link with a knife. The charger then only charges between about 1 °C and 46 °C. Don't fit the NTC without cutting JP2, or the sensing stays off.

## Dimensions

| | |
|---|---|
| Board outline | 14.4 × 12.2 mm (0.57 × 0.48 in), square corners |
| Board thickness | 1.6 mm |
| Overall thickness | about 3.4 mm with parts (the CN3163 is the tallest at up to 1.75 mm), plus your wires and solder |
| Wire pads | 1.4 × 1.5 mm, 2 mm apart centre to centre |
| Pad rows | centres 1.3 mm in from the top and bottom edges; pads start 0.55 mm from the edge |
| Top row, from the left edge | NTC 2.2 and 4.2 mm, OUT − 6.2 and + 8.2 mm, SW 10.2 and 12.2 mm |
| Bottom row, from the left edge | SOL + 1.25 and − 3.25 mm, BAT + 11.15 and − 13.15 mm |
| Mounting holes | none |

The width and height are also marked on the top and bottom pictures.

## Specifications

- Board: 14.4 × 12.2 mm, 1.6 mm FR-4, 2 layers, square corners (V-score panel friendly). No mounting holes
- Pads: 1.4 × 1.5 mm SMD at 2 mm pitch, for wires up to ~24 AWG
- Current: 1 A maximum on any net
- Solar input: 4.4–6 V. **Absolute maximum 6.5 V**: use a 5 V panel whose open-circuit voltage stays under 6.5 V. No reverse-polarity protection on the panel input.
- Battery reverse-polarity protection: AO3401A P-MOSFET in the battery + line, gate to GND. A correctly connected cell turns it fully on (~60 mΩ, both directions, so charging works through it); a reversed cell leaves it off and nothing on the board sees the wrong polarity.
- Charging: 4.2 V float, 0.99 A maximum (R1 = 1.2 kΩ). The CN3163 lowers the current by itself when the panel sags toward 4.4 V or the chip reaches ~130 °C. On a board this small it will run hot and throttle at full current, which is normal.
- Battery temperature (optional): 10 kΩ B3950 NTC on the NTC pads, JP2 cut. Charging is suspended outside ~1–46 °C (4.7 kΩ / 47 kΩ divider from the panel input). With JP2 closed the divider draws ~1 mA from the panel while the sun is up.
- Status LEDs: red = charging, green = charge complete. Enabled by bridging JP1 (open by default). They're powered from the panel, so they're off without sun.
- Parts: CN3163 (eSOP-8), AO3401A (SOT-23), 1.2 kΩ 1 %, 2 × 10 µF 10 V (0603); red and green LEDs, 2 × 1 kΩ, 4.7 kΩ and 47 kΩ 1 % (0402). Top side only

## Schematic

![Schematic](docs/images/schematic.svg)

## Back

![Bottom](docs/images/pcb-bottom.png)

The back carries the short name (SNAP Power Mini), the limits and a warning:

| Printed | Meaning |
|---|---|
| CHECK POLARITY | Check + and − on every wire before connecting. The battery input survives a reversed cell; the solar input and the load output have no protection |
| SOL MAX 6V 1A | Solar panel: 6 V maximum in normal use, and never above 6.5 V open-circuit. The charger draws at most 1 A; a panel that can supply more is fine as long as its voltage is within the limit |
| OUT MAX 1A | Load: 1 A maximum, continuous. There is no fuse and no over-current or low-voltage cut-off on the output, so use a protected cell |
| AS IS NO WARRANTY | See the disclaimer below |

Under the text, the back is a ground plane with two jumpers (battery + up to the charger's sense pin, and the panel input round to the LED jumper) and six thermal vias under the CN3163.

## Fabrication

The package is generated into `output/fab/`. It isn't tracked in git; regenerate it with the commands in `CLAUDE.md`.

| File | Contents |
|---|---|
| `SNAP_Power_Mini_v2.0_gerbers.zip` | Upload this to the board house: Gerbers incl. solder paste, drill files, job file. 2 layers, 1.6 mm, 1 oz copper |
| `SNAP_Power_Mini_v2.0_BOM.csv` | BOM in JLCPCB format with LCSC part numbers for every line |
| `SNAP_Power_Mini_v2.0_CPL.csv` | Pick-and-place file, top side only, same coordinates as the Gerbers |
| `FAB_NOTES.txt` | Order settings and assembly cautions |

The CN3163 (C559031) and the two LEDs are JLCPCB Extended parts; the AO3401A is C15127. Check the rotation of U1 and Q1 and the polarity of the LEDs in the assembler's preview before ordering. The wire pads and the two solder jumpers aren't parts, so they're not in the BOM or placement file.

## Disclaimer

This board is a hobby design for people who know how to handle lithium cells. It has not been tested or certified to any safety standard (UL, CE, FCC, UN 38.3 or other). Lithium-ion cells can catch fire or explode if they are over-charged, short-circuited, reverse-connected, punctured or charged outside their temperature range. You are responsible for checking polarity, staying within the limits printed on the board, choosing a protected cell, and deciding whether the board suits your use.

THE DESIGN FILES AND ANY BOARD MADE FROM THEM ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE AUTHOR IS NOT LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL OR CONSEQUENTIAL DAMAGES, INCLUDING DAMAGE TO BATTERIES, PANELS OR CONNECTED EQUIPMENT, LOSS OF DATA, FIRE OR INJURY, AND THE AUTHOR'S TOTAL LIABILITY FOR ANY CLAIM IS LIMITED TO THE PRICE PAID FOR THE BOARD.

Some jurisdictions do not allow the exclusion of implied warranties or the limitation of liability for certain damages, so parts of the above may not apply to you; nothing here limits rights that cannot be limited by law.

## Regenerating the design

The schematic and board are generated by the scripts in `tools/`; see `CLAUDE.md` for the commands.
