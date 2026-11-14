# SPDX-License-Identifier: MIT
# Writes the project footprints into SNAP_Power_Mini.pretty. Run from the repo root with KiCad's Python:
#   "C:/Program Files/KiCad/10.0/bin/python.exe" tools/make-footprints.py
import pathlib
LIB = pathlib.Path("SNAP_Power_Mini.pretty")
def prop(name, value, x, y, layer, hide, size=0.8):
    return f'''	(property "{name}" "{value}"
		(at {x} {y} 0)
		(layer "{layer}")
		{"(hide yes)" if hide else ""}
		(effects
			(font
				(size {size} {size})
				(thickness {round(size*0.15, 3)})
			)
		)
	)'''
def rect(x0, y0, x1, y1, layer, w):
    return f'''	(fp_rect
		(start {x0} {y0})
		(end {x1} {y1})
		(stroke
			(width {w})
			(type solid)
		)
		(fill no)
		(layer "{layer}")
	)'''
def smd(num, x, y, sx, sy, rr=0.1, paste=False):
    layers = '"F.Cu" "F.Mask" "F.Paste"' if paste else '"F.Cu" "F.Mask"'
    return f'''	(pad "{num}" smd roundrect
		(at {x} {y})
		(size {sx} {sy})
		(layers {layers})
		(roundrect_rratio {rr})
	)'''
def write(name, descr, tags, attr, body, ref_y):
    text = "\n".join([f'(footprint "{name}"', '\t(version 20260206)', '\t(generator "pcbnew")', '\t(generator_version "10.0")',
        '\t(layer "F.Cu")', f'\t(descr "{descr}")', f'\t(tags "{tags}")',
        prop("Reference", "REF**", 0, ref_y, "F.Fab", False), prop("Value", name, 0, -ref_y, "F.Fab", True),
        prop("Datasheet", "", 0, 0, "F.Fab", True, 1.27), prop("Description", "", 0, 0, "F.Fab", True, 1.27),
        f'\t(attr {attr})', '\t(duplicate_pad_numbers_are_jumpers no)', *body, '\t(embedded_fonts no)', ')', ''])
    (LIB / f"{name}.kicad_mod").write_text(text, encoding="utf-8", newline="\n")

PW, PH, P = 1.4, 1.5, 2.0   # wire pad size and pitch
CY = 0.25                   # courtyard margin
def wirepads(n, order):
    xs = [(i - (n - 1) / 2) * P for i in range(n)]
    body = [rect(round(x - PW/2, 3), -PH/2, round(x + PW/2, 3), PH/2, "F.Fab", 0.1) for x in xs]
    body.append(rect(round(xs[0] - PW/2 - CY, 3), -PH/2 - CY, round(xs[-1] + PW/2 + CY, 3), PH/2 + CY, "F.CrtYd", 0.05))
    body += [smd(num, round(x, 3), 0, PW, PH) for num, x in zip(order, xs)]
    return body
write("WirePad_1x02_SMD_1.4x1.5mm_P2.0mm",
      "Pair of SMD wire solder pads side by side, 1.4x1.5mm, 2.0mm pitch, for hand-soldered wires up to ~24 AWG (1 A). No silkscreen: labels are on the board.",
      "solder wire pad SMD pair", "smd exclude_from_pos_files exclude_from_bom", wirepads(2, ["1", "2"]), 1.6)
# Normally open solder jumper: 0.6 x 0.8 mm pads, 0.3 mm gap, bridged by hand with a blob of solder.
# Never populated, so the courtyard is only 0.1 mm outside the pads.
jp = [rect(-0.75, -0.4, 0.75, 0.4, "F.Fab", 0.1), rect(-0.85, -0.5, 0.85, 0.5, "F.CrtYd", 0.05),
      smd("1", -0.45, 0, 0.6, 0.8, 0.15), smd("2", 0.45, 0, 0.6, 0.8, 0.15)]
write("SolderJumper-2_P0.9mm_Open_Pad0.6x0.8mm",
      "Tiny normally open solder jumper, 0.6x0.8mm pads, 0.3mm gap; close with a solder blob.",
      "solder jumper open SPST", "smd exclude_from_pos_files exclude_from_bom", jp, 1.0)
# Normally closed version: the same pads joined by a 0.3 mm copper link (a net tie, so DRC accepts
# the two nets touching); cut the link with a knife to open it.
link = '''	(fp_poly
		(pts
			(xy -0.15 -0.15) (xy 0.15 -0.15) (xy 0.15 0.15) (xy -0.15 0.15)
		)
		(stroke
			(width 0)
			(type solid)
		)
		(fill yes)
		(layer "F.Cu")
	)'''
write("SolderJumper-2_P0.9mm_Bridged_Pad0.6x0.8mm",
      "Tiny normally closed solder jumper, 0.6x0.8mm pads joined by a 0.3mm copper link; cut the link to open it.",
      "solder jumper closed SPST", "smd exclude_from_pos_files exclude_from_bom allow_soldermask_bridges",
      ['	(net_tie_pad_groups "1, 2")'] + jp + [link], 1.0)
