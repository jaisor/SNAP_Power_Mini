# Builds the whole SNAP Mini Power Controller board from the schematic netlist: footprints placed and linked to
# their symbols, hand-placed tracks and vias, GND pours on both layers, silkscreen, and a
# square-cornered 14.4 x 12.2 mm outline (V-score panel friendly).
# Run with KiCad's Python:
#   "C:\Program Files\KiCad\10.0\bin\python.exe" tools/build-pcb.py <netlist.xml> [project dir, default: repo root]
# Netlist: kicad-cli sch export netlist --format kicadxml -o output/net.xml SNAP_Power_Mini.kicad_sch
#
# Layout (top view), no mounting holes. Two rows of wire pads with the charger between them:
#   NTC   -OUT+   SW                 top row:    J5, J3, J2 (SW_B = OUT+ bridged on F.Cu)
#   R4 R5 JP2 |        | D1 R2 JP1   left of U1:  NTC network above R1 (ISET)
#      R1     | CN3163 | D2 R3       right of U1: status LEDs + resistors, JP1, above C2 (BAT)
#             |        |   C2
#   +SOL-  C1   Q1   +BAT-           bottom row: J4, C1 (VIN) and Q1 (reverse-battery guard), J1
# The 0402 parts and the jumpers stand vertically to keep the board narrow.
# F.Cu: VIN from SOL+ along the bottom to C1 and pin 4, and up the left edge to R4; BAT+ from SW_A
# along the top to FB (pin 8); Q1's drain runs under its own body to BAT+ pad.
# B.Cu jumpers: BAT+ (pin 5 / Q1 source up to pin 8) and VIN (from C1 round the bottom-right
# corner up to JP1).
# No net carries more than 1 A: 0.4 mm power tracks, 0.3 mm vias.
import os
import sys
import xml.etree.ElementTree as ET

import pcbnew

FPDIR = "C:/Program Files/KiCad/10.0/share/kicad/footprints"
NAME = "SNAP_Power_Mini"
ORIGIN = (100.0, 100.0)  # board top-left in the editor, mm
W, H = 14.4, 12.2  # board size, mm
CORNER = 0.0  # outline corner radius, mm; 0 = sharp corners so panels can be V-scored
TOP_ROW_Y = 1.3  # top pad row centres (pads 1.5 mm tall, 0.55 mm from the edge)
BOT_ROW_Y = H - 1.3  # bottom pad row centres
UX, UY = 7.2, 5.95  # U1 centre
ZONE_CLEAR = 0.25

# ref: (x, y, rotation) of the footprint origin, mm from the board's top-left corner.
PLACEMENT = {
    "J5": (3.2, TOP_ROW_Y, 180),  # NTC:     2 = GND (x 2.2), 1 = TEMP (x 4.2)
    "J3": (7.2, TOP_ROW_Y, 180),  # LOAD:    2 = GND (x 6.2), 1 = VOUT (x 8.2)
    "J2": (11.2, TOP_ROW_Y, 180),  # SWITCH:  2 = VOUT (x 10.2), 1 = BAT+ (x 12.2)
    "J4": (2.25, BOT_ROW_Y, 0),  # SOLAR:   1 = VIN (x 1.25), 2 = GND (x 3.25)
    "J1": (12.15, BOT_ROW_Y, 0),  # BATTERY: 1 = BAT_IN (x 11.15), 2 = GND (x 13.15)
    "U1": (UX, UY, 0),  # CN3163: pins 1-4 down the left (VIN = 4), 5-8 up the right (BAT = 5)
    # Left of U1, vertical: TEMP pads up, VIN / GND pads down
    "R4": (0.82, 4.17, 90),  # VIN (pad 1, bottom) to TEMP (pad 2, top)
    "R5": (1.86, 4.17, 270),  # TEMP (pad 1, top) to GND
    "JP2": (2.88, 4.17, 270),  # TEMP (pad 1, top) to GND, closed until cut
    "R1": (2.7, 7.0, 270),  # ISET (pad 1, top) to GND
    # Bottom row, between the solar and battery pads
    "C1": (4.98, 10.17, 270),  # VIN bypass under pin 4; pad 1 (VIN) up
    "Q1": (7.735, 10.395, 180),  # drain (pin 3) left, source (2) top-right under pin 5, gate (1) GND
    # Right of U1, vertical
    "D1": (11.42, 4.17, 90),  # red, CHRG: cathode (pad 1) down toward pin 7
    "R2": (12.46, 4.17, 270),  # D1 anode (pad 1, top) to LED_PWR
    "JP1": (13.48, 4.17, 90),  # LED_PWR (pad 1, bottom) to VIN (pad 2, top), open until bridged
    "D2": (11.42, 6.11, 270),  # green, DONE: cathode (pad 1) up, level with the track from pin 6
    "R3": (12.46, 6.11, 90),  # D2 anode (pad 1, bottom) to LED_PWR
    "C2": (12.42, 7.97, 0),  # BAT capacitor next to pin 5; pad 1 toward the IC
}
PWR, SIG, GND_W = 0.4, 0.25, 0.3  # track widths, mm
VIA = (0.6, 0.3)  # diameter, drill
# Tracks: (net, layer, width, points). A point is (x, y) or (ref, pad) for that pad's centre.
TRACKS = [
    ("/VOUT", "F", 1.0, [("J3", "1"), ("J2", "2")]),
    # VIN: SOL+ along the bottom to C1 and up to pin 4; up the left edge to R4; via by C1, then
    # B.Cu along the bottom and up the right edge to a via above JP1
    ("/VIN", "F", PWR, [("J4", "1"), (1.25, 9.5), (4.6, 9.5), ("C1", "1"), ("U1", "4")]),
    ("/VIN", "F", SIG, [("R4", "1"), (0.82, 9.1), (1.25, 9.5)]),
    ("/VIN", "F", SIG, [("C1", "1"), (5.7, 9.25), (6.2, 9.25)]),
    ("/VIN", "B", SIG, [(6.2, 9.25), (6.6, 9.65), (13.35, 9.65), (13.75, 9.25), (13.75, 3.1), (13.5, 2.85)]),
    ("/VIN", "F", SIG, [(13.5, 2.85), ("JP1", "2")]),
    # Battery pad -> Q1 drain (under Q1's body, between its other two pads); Q1 source -> pin 5
    # and C2; B.Cu from the via by pin 5 up to the via by pin 8; SW_A along the top to pin 8
    ("/BAT_IN", "F", PWR, [("Q1", "3"), (10.6, 10.395), ("J1", "1")]),
    ("/BAT+", "F", PWR, [("Q1", "2"), (9.6, 8.7), ("U1", "5"), ("C2", "1")]),
    ("/BAT+", "B", PWR, [(9.6, 8.7), (9.6, 3.1)]),
    ("/BAT+", "F", PWR, [("J2", "1"), (12.2, 2.6), (11.85, 2.95), (9.9, 2.95), (9.6, 3.1), ("U1", "8")]),
    # TEMP: NTC pad straight down into pin 1; R4, R5 and JP2 joined along their top pads
    ("/TEMP", "F", SIG, [("J5", "1"), (4.2, 4.045)]),
    ("/TEMP", "F", SIG, [("R4", "2"), ("R5", "1"), ("JP2", "1"), (4.2, 3.72)]),
    ("GND", "F", GND_W, [("JP2", "2"), ("R5", "2"), (1.75, 5.45)]),
    # ISET resistor, kept short (datasheet layout note 1)
    ("Net-(U1-ISET)", "F", SIG, [("U1", "2"), (3.3, 5.6), ("R1", "1")]),
    ("GND", "F", GND_W, [("R1", "2"), (1.7, 7.775)]),
    # Status LEDs: pins -> cathodes, anodes -> resistors -> JP1
    ("Net-(D1-K)", "F", SIG, [("U1", "7"), (10.6, 5.1), (10.95, 4.655), ("D1", "1")]),
    ("Net-(D2-K)", "F", SIG, [("U1", "6"), (10.5, 6.585), (11.0, 5.75), ("D2", "1")]),
    ("Net-(D1-A)", "F", SIG, [("D1", "2"), ("R2", "1")]),
    ("Net-(D2-A)", "F", SIG, [("D2", "2"), ("R3", "1")]),
    ("/LED_PWR", "F", SIG, [("JP1", "1"), ("R2", "2"), ("R3", "2")]),
    # GND: pin 3 into the exposed pad; C1 to SOL-; C2 to BAT-; Q1's gate to a via
    ("GND", "F", GND_W, [("U1", "3"), (6.4, 6.585)]),
    ("GND", "F", PWR, [("J4", "2"), ("C1", "2")]),
    ("GND", "F", PWR, [("C2", "2"), ("J1", "2")]),
    ("GND", "F", GND_W, [("Q1", "1"), (7.25, 11.345)]),
]
VIAS = {
    "/VIN": [(6.2, 9.25), (13.5, 2.85)],
    "/BAT+": [(9.6, 8.7), (9.6, 3.1)],
    # The NTC network's and R1's returns, Q1's gate, vias in the NTC-, OUT-, SOL- and BAT- pads,
    # and six thermal vias in U1's exposed pad
    "GND": [(1.75, 5.45), (1.7, 7.775), (7.25, 11.345), (2.2, TOP_ROW_Y), (5.8, TOP_ROW_Y), (6.6, TOP_ROW_Y),
            (2.85, BOT_ROW_Y), (3.65, BOT_ROW_Y), (12.75, BOT_ROW_Y), (13.55, BOT_ROW_Y)]
    + [(x, y) for x in (UX - 0.6, UX + 0.6) for y in (UY - 1.1, UY, UY + 1.1)],
}

# Silkscreen: pad names between each pad row and the parts.
LABELS = [("NTC", 3.2, 2.7), ("-OUT+", 7.2, 2.7), ("SW", 11.2, 2.7),
          ("+SOL-", 2.25, H - 2.7), ("+BAT-", 12.15, H - 2.7)]
LABEL_TEXT = 0.8
# Back: name, warnings and ratings in the bands between the vias. (text, height, y, x of the text's
# centre). x is in board coordinates like everything else, so on the back, which is seen mirrored,
# a larger x is further left: the two ratings rows read "SOL MAX | 6V 1A" and "OUT MAX | 1A" with
# U1's thermal vias between the columns.
BACK_TEXT = [
    ("SNAP Power Mini", 0.8, 2.2, W / 2),
    ("CHECK POLARITY", 0.8, 3.97, W / 2),
    ("SOL MAX", 0.8, 5.3, 11.1), ("6V 1A", 0.8, 5.3, 4.05),
    ("OUT MAX", 0.8, 6.6, 11.1), ("1A", 0.8, 6.6, 4.05),
    ("JaisorGadgets", 0.8, 7.9, W / 2),
    ("AS IS NO WARRANTY", 0.8, 10.07, W / 2),
    ("v2.0", 0.8, 11.2, 10.0),
]


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))


def silk_text(board, text, x, y, height, layer=pcbnew.F_SilkS, thickness=0.15):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(height), mm(height)))
    t.SetTextThickness(mm(thickness))
    t.SetMirrored(layer == pcbnew.B_SilkS)
    t.SetPosition(pt(x, y))
    board.Add(t)
    return t


def edge_outline(board):
    c = CORNER
    lines = [((c, 0), (W - c, 0)), ((W, c), (W, H - c)), ((W - c, H), (c, H)), ((0, H - c), (0, c))]
    for a, b in lines:
        seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(pt(*a))
        seg.SetEnd(pt(*b))
        seg.SetWidth(mm(0.05))
        board.Add(seg)
    if c == 0:
        return
    k = c * (1 - 0.5 ** 0.5)  # 45-degree point on each corner arc
    arcs = [((0, c), (k, k), (c, 0)), ((W - c, 0), (W - k, k), (W, c)),
            ((W, H - c), (W - k, H - k), (W - c, H)), ((c, H), (k, H - k), (0, H - c))]
    for a, m, b in arcs:
        arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        arc.SetLayer(pcbnew.Edge_Cuts)
        arc.SetArcGeometry(pt(*a), pt(*m), pt(*b))
        arc.SetWidth(mm(0.05))
        board.Add(arc)


def add_gnd_zone(board, layer, net):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(net)
    e = 0.5  # board-edge copper clearance
    for x, y in [(e, e), (W - e, e), (W - e, H - e), (e, H - e)]:
        z.AppendCorner(pt(x, y), -1)
    z.SetLocalClearance(mm(ZONE_CLEAR))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)
    return z


def main():
    netfile = sys.argv[1]
    proj = sys.argv[2] if len(sys.argv) > 2 else "."
    pcb_path = os.path.join(proj, NAME + ".kicad_pcb")
    root = ET.parse(netfile).getroot()

    board = pcbnew.NewBoard(pcb_path)
    tb = board.GetTitleBlock()
    tb.SetTitle("SNAP Mini Power Controller")
    tb.SetRevision("0.2")
    tb.SetDate("2026-10-30")
    tb.SetComment(0, "Solar -> CN3163 -> Q1 -> battery; switch -> load; battery NTC. 14.4 x 12.2 mm")

    fps = {}
    for comp in root.iter("comp"):
        ref = comp.get("ref")
        lib, name = comp.findtext("footprint").split(":")
        libdir = os.path.join(proj, f"{lib}.pretty") if lib == NAME else f"{FPDIR}/{lib}.pretty"
        fp = pcbnew.FootprintLoad(libdir, name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(comp.findtext("value"))
        # Mirror the symbol's fields so the schematic-parity DRC check stays clean.
        for field, tag in (("Datasheet", "datasheet"), ("Description", "description")):
            if comp.findtext(tag) is not None:
                fp.SetField(field, comp.findtext(tag))
        # Link to the schematic symbol so "Update PCB from Schematic" matches instead of duplicating.
        sheet = comp.find("sheetpath").get("tstamps")
        fp.SetPath(pcbnew.KIID_PATH(sheet + comp.findtext("tstamps")))
        fp.SetSheetname(comp.find("sheetpath").get("names"))
        fp.SetSheetfile(NAME + ".kicad_sch")
        if ref not in PLACEMENT:
            sys.exit(f"no placement for {ref}")
        x, y, rot = PLACEMENT[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pt(x, y))
        # No room for reference labels on a board this size; the Fab layer keeps them.
        fp.Reference().SetVisible(False)
        board.Add(fp)
        fps[ref] = fp

    nets = {}
    for net in root.iter("net"):
        ni = pcbnew.NETINFO_ITEM(board, net.get("name"))
        board.Add(ni)
        nets[net.get("name")] = ni
        for node in net.iter("node"):
            pads = [p for p in fps[node.get("ref")].Pads() if p.GetNumber() == node.get("pin")]
            if not pads:
                sys.exit(f"{node.get('ref')} has no pad {node.get('pin')}")
            for p in pads:
                p.SetNet(ni)
    code = {name: ni.GetNetCode() for name, ni in nets.items()}

    def pad_xy(ref, num):
        pads = [p for p in fps[ref].Pads() if p.GetNumber() == num]
        c = pads[0].GetPosition()
        return pcbnew.ToMM(c.x) - ORIGIN[0], pcbnew.ToMM(c.y) - ORIGIN[1]

    for name, layer, width, points in TRACKS:
        xy = [pad_xy(*p) if isinstance(p[0], str) else p for p in points]
        for a, b in zip(xy, xy[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(*a))
            t.SetEnd(pt(*b))
            t.SetWidth(mm(width))
            t.SetLayer(pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu)
            t.SetNetCode(code[name])
            board.Add(t)
    for name, centres in VIAS.items():
        for c in centres:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pt(*c))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(mm(VIA[0]))
            v.SetDrill(mm(VIA[1]))
            v.SetNetCode(code[name])
            board.Add(v)
    zones = [add_gnd_zone(board, pcbnew.F_Cu, code["GND"]), add_gnd_zone(board, pcbnew.B_Cu, code["GND"])]

    for text, x, y in LABELS:
        silk_text(board, text, x, y, LABEL_TEXT, thickness=0.12)
    # Back: name, warnings, ratings; a line is shrunk only if it is wider than the board less 1 mm a side.
    for text, height, y, x in BACK_TEXT:
        t = silk_text(board, text, x, y, height, layer=pcbnew.B_SilkS, thickness=0.1)
        width = pcbnew.ToMM(t.GetEffectiveTextShape().BBox().GetWidth())
        room = W - 2 * 1.0
        print(f"back text {text!r}: {width:.2f} mm wide, x {x - width / 2:.2f}..{x + width / 2:.2f}")
        if width > room:
            s = height * room / width
            t.SetTextSize(pcbnew.VECTOR2I(mm(s), mm(s)))

    edge_outline(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb_path, board)
    print(f"board {W} x {H} mm, {len(fps)} footprints, {board.GetNetCount()} nets, "
          f"{sum(len(v) for v in VIAS.values())} vias, {len(zones)} GND zones")
    for ref in ("U1", "R1", "C1", "C2", "D1", "R2", "D2", "R3", "JP1", "JP2", "R4", "R5", "Q1"):
        print(ref, {p.GetNumber(): tuple(round(v, 3) for v in pad_xy(ref, p.GetNumber())) for p in fps[ref].Pads() if p.GetNumber()})


main()
