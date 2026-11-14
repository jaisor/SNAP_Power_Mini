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
| SOL MAX 6V 1A | Solar panel: 6 V and 1 A; see the limits under [Safety](#safety) |
| OUT MAX 1A | Load: 1 A maximum |
| AS IS NO WARRANTY | See [Safety](#safety) and the [licence](#license) |

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

## Safety

This is an experimental design for charging a lithium-ion cell. It's provided as is, with no warranty, and hasn't been certified to any safety standard. If you build it, you're responsible for:

- Assembling it correctly and checking polarity before connecting a panel, a cell or a load. Q1 protects against a reversed cell on the battery pads, but the solar input and the load output have no protection, and a battery soldered to the solar pads is not covered either.
- Using a protected cell or a separate protection circuit. The CN3163 charges the cell but doesn't protect it from over-discharge or short circuits, and the board has no fuse.
- Fusing, wiring and an enclosure suited to where the node is used, including outdoor heat and moisture.
- Not using it where a failure could hurt someone or damage property.

**Limits**, also printed on the back of the board:

| | Limit | Set by |
|---|---|---|
| Battery | One Li-ion or LiPo cell (1S), charged to 4.2 V | The CN3163's fixed charge voltage |
| Panel voltage | 6 V in use, and never above 6.5 V open-circuit. Use a 5 V panel | The CN3163's absolute maximum rating; nothing sits between the pads and the chip |
| Panel current | The charger draws 1 A at most. A panel that can supply more is fine if its voltage is within the limit | R1 (charge current) |
| Load on OUT | 1 A | The tracks and vias |

**No warranty:** the board is provided as is, and you use it at your own risk. Where the law allows a limit, liability for a board you bought is limited to the price you paid for it. The design itself is covered by the disclaimer in the [licence](#license).

## Regenerating the design

The schematic and board are generated by the scripts in `tools/`; see `CLAUDE.md` for the commands.

## License

Copyright 2026 Jordan Marinov (JaisorGadgets).

The hardware design (schematic, board, symbol and footprint libraries) and its documentation, including the images in `docs/images/`, are licensed under the [CERN Open Hardware Licence Version 2 – Permissive](LICENSE) (CERN-OHL-P-2.0). You may redistribute and modify them, and make and sell products from them, under the terms of the licence. They are distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A PARTICULAR PURPOSE. See section 5 of the licence for the disclaimer and limitation of liability.

The scripts in `tools/` are licensed under the [MIT License](tools/LICENSE).
