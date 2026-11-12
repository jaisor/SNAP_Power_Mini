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

The back is a ground plane with two jumpers (battery + up to the charger's sense pin, and the panel input round to the LED jumper) and six thermal vias under the CN3163.

## Fabrication

The package is generated into `output/fab/`. It isn't tracked in git; regenerate it with the commands in `CLAUDE.md`.

| File | Contents |
|---|---|
| `SNAP_Power_Mini_v2.0_gerbers.zip` | Upload this to the board house: Gerbers incl. solder paste, drill files, job file. 2 layers, 1.6 mm, 1 oz copper |
| `SNAP_Power_Mini_v2.0_BOM.csv` | BOM in JLCPCB format with LCSC part numbers for every line |
| `SNAP_Power_Mini_v2.0_CPL.csv` | Pick-and-place file, top side only, same coordinates as the Gerbers |
| `FAB_NOTES.txt` | Order settings and assembly cautions |

The CN3163 (C559031) and the two LEDs are JLCPCB Extended parts; the AO3401A is C15127. Check the rotation of U1 and Q1 and the polarity of the LEDs in the assembler's preview before ordering. The wire pads and the two solder jumpers aren't parts, so they're not in the BOM or placement file.

## Regenerating the design

The schematic and board are generated by the scripts in `tools/`; see `CLAUDE.md` for the commands.
