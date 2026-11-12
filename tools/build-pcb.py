# Builds the whole SNAP Mini Power Controller board from the schematic netlist: footprints placed and linked to
# their symbols, hand-placed tracks and vias, GND pours on both layers kept clear of the M2
# holes, silkscreen, and a square-cornered 20 x 15 mm outline (V-score panel friendly).
# Run with KiCad's Python:
#   "C:\Program Files\KiCad\10.0\bin\python.exe" tools/build-pcb.py <netlist.xml> [project dir, default: repo root]
# Netlist: kicad-cli sch export netlist --format kicadxml -o output/net.xml SNAP_Power_Mini.kicad_sch
#
# Layout (top view). Top band, between the corner M2 holes:
#   (H1)  -BAT+  SW  +OUT-  (H2)     J1, J2, J3 pairs; SW_B = OUT+ bridged on F.Cu
# Below them Q1 AO3401A (reverse-battery guard): battery pad -> drain, source -> SW_A and BAT+.
# Middle band: R1 (ISET) and C1 (VIN) left of U1 CN3163; right of it the status LEDs in two
# rows (D1 red + R2 on CHRG, D2 green + R3 on DONE, 0402) above C2 (BAT); JP1 (LED enable,
# normally open) above them, between the VIN bus and the LED resistors.
# Under each hole a column of two SOD-323 Schottkys, anodes toward the ends of the column,
# cathodes joined in the middle (VIN).
# Bottom edge: J4, S1+ S2+ GND S3+ S4+ spread across the full width, double-size return.
# F.Cu: VIN bus straight across from the left diode column to the right one, between Q1 and the
# IC; S1 and S4 run straight down from the lower diodes.
# B.Cu jumpers: S2 and S3 down from the upper diodes, BAT+ -> FB and BAT pins, VIN -> C1/pin 4.
# No net carries more than 1 A: 0.4 mm power tracks, 0.3 mm vias.
import math
import os
import sys
import xml.etree.ElementTree as ET

import pcbnew

FPDIR = "C:/Program Files/KiCad/10.0/share/kicad/footprints"
NAME = "SNAP_Power_Mini"
ORIGIN = (100.0, 100.0)  # board top-left in the editor, mm
W, H = 20.0, 15.0  # board size, mm
CORNER = 0.0  # outline corner radius, mm; 0 = sharp corners so panels can be V-scored
HOLE_XY = 2.0  # M2 hole centres 2 mm in from the top and side edges
HOLE_R = 1.05  # 2.1 mm drill
HOLE_KEEPOUT = 2.0  # no copper within this radius of a hole centre (4 mm M2 head / standoff)
TOP_ROW_Y = 1.3  # J1-J3 pad centres (pads 1.5 mm tall)
SOLAR_ROW_Y = H - 1.3  # J4 pad centres, 0.55 mm copper margin to the bottom edge
ZONE_CLEAR = 0.25

# ref: (x, y, rotation) of the footprint origin, mm from the board's top-left corner.
PLACEMENT = {
    "H1": (HOLE_XY, HOLE_XY, 0),
    "H2": (W - HOLE_XY, HOLE_XY, 0),
    "J1": (6.0, TOP_ROW_Y, 180),  # BATTERY: 2 = GND (x 5), 1 = BAT_IN (x 7)
    "J2": (10.0, TOP_ROW_Y, 0),  # SWITCH:  1 = BAT+ (x 9), 2 = VOUT (x 11)
    "J3": (14.0, TOP_ROW_Y, 0),  # LOAD:    1 = VOUT (x 13), 2 = GND (x 15)
    # Drain (pin 3) left under the battery pad, source (2) up under SW_A, gate (1) GND
    "Q1": (8.0, 4.75, 180),
    "J4": (10.0, SOLAR_ROW_Y, 0),  # SOLAR: S1 1.25, S2 5.275, GND 10 (2.8 mm wide), S3 14.725, S4 18.75
    # Schottkys, cathode (pad 1) toward the middle of each column
    "D4": (1.5, 5.7, 90),  # S2, anode up
    "D3": (1.5, 9.05, 270),  # S1, anode down
    "D5": (18.7, 5.7, 90),  # S3, anode up
    "D6": (18.7, 9.05, 270),  # S4, anode down
    "U1": (10.0, 9.25, 0),  # CN3163: pins 1-4 down the left (VIN = 4), 5-8 up the right (BAT = 5)
    "R1": (4.6, 8.615, 180),  # in line with ISET (pin 2); pad 1 toward the IC
    "C1": (4.7, 11.0, 180),  # VIN bypass next to pin 4; pad 1 toward the IC
    "C2": (15.3, 11.0, 0),  # BAT capacitor next to pin 5; pad 1 toward the IC
    "D1": (14.75, 8.4, 0),  # red, CHRG: cathode (pad 1) toward pin 7
    "R2": (16.7, 8.4, 0),
    "D2": (14.75, 9.6, 0),  # green, DONE: cathode (pad 1) toward pin 6
    "R3": (16.7, 9.6, 0),
    "JP1": (16.0, 7.2, 180),  # pad 2 (VIN, left) up to the bus, pad 1 (LED_PWR, right) to R2/R3
}
PWR, SIG, SOL, GND_W = 0.4, 0.25, 0.3, 0.3  # track widths, mm
VIA = (0.6, 0.3)  # diameter, drill
# Tracks: (net, layer, width, points). A point is (x, y) or (ref, pad) for that pad's centre.
TRACKS = [
    ("/VOUT", "F", 1.0, [("J2", "2"), ("J3", "1")]),
    # Battery pad straight down to Q1's drain; Q1's source up to SW_A and across to a BAT+ via,
    # then B.Cu down beside the IC to the vias at pins 8 and 5
    ("/BAT_IN", "F", PWR, [("J1", "1"), ("Q1", "3")]),
    ("/BAT+", "F", PWR, [("Q1", "2"), ("J2", "1")]),
    ("/BAT+", "F", PWR, [("Q1", "2"), (13.4, 3.8), (13.85, 4.25), (13.85, 5.0)]),
    ("/BAT+", "B", PWR, [(13.85, 5.0), (13.85, 11.155)]),
    ("/BAT+", "F", PWR, [("U1", "8"), (13.85, 7.345)]),
    ("/BAT+", "F", PWR, [("U1", "5"), (13.85, 11.155), ("C2", "1")]),
    # Panels: S1 and S4 straight down from the lower diodes; S2 and S3 on B.Cu from the upper ones
    ("/SOL1", "F", SOL, [("D3", "2"), ("J4", "1")]),
    ("/SOL4", "F", SOL, [("D6", "2"), ("J4", "4")]),
    ("/SOL2", "F", SOL, [("D4", "2"), (2.7, 5.1)]),
    ("/SOL2", "B", SOL, [(2.7, 5.1), (2.7, 12.3), (3.8, SOLAR_ROW_Y), ("J4", "2")]),
    ("/SOL3", "F", SOL, [("D5", "2"), (17.6, 5.1)]),
    ("/SOL3", "B", SOL, [(17.6, 5.1), (17.6, 12.3), (16.5, SOLAR_ROW_Y), ("J4", "3")]),
    # VIN: cathode pairs joined, bus between Q1 and the IC with a stub down to JP1's VIN pad;
    # B.Cu jumper to C1/pin 4
    ("/VIN", "F", PWR, [("D4", "1"), ("D3", "1")]),
    ("/VIN", "F", PWR, [("D5", "1"), ("D6", "1")]),
    ("/VIN", "F", PWR, [("D4", "1"), (1.9, 6.4), (18.3, 6.4), ("D5", "1")]),
    ("/VIN", "F", PWR, [(15.55, 6.4), ("JP1", "2")]),
    ("/VIN", "F", PWR, [(5.6, 6.4), (5.6, 7.1)]),
    ("/VIN", "B", PWR, [(5.6, 7.1), (5.6, 10.55), (6.2, 11.155)]),
    ("/VIN", "F", PWR, [("C1", "1"), (6.2, 11.155), ("U1", "4")]),
    # Status LEDs: JP1 -> resistors -> anodes; cathodes -> CHRG/DONE pins
    ("/LED_PWR", "F", SIG, [("JP1", "1"), (17.21, 7.2), ("R2", "2"), ("R3", "2")]),
    ("Net-(D1-K)", "F", SIG, [("U1", "7"), (13.7, 8.615), ("D1", "1")]),
    ("Net-(D2-K)", "F", SIG, [("U1", "6"), (13.7, 9.885), ("D2", "1")]),
    ("Net-(D1-A)", "F", SIG, [("D1", "2"), ("R2", "1")]),
    ("Net-(D2-A)", "F", SIG, [("D2", "2"), ("R3", "1")]),
    # ISET resistor, kept short (datasheet layout note 1)
    ("Net-(U1-ISET)", "F", SIG, [("R1", "1"), ("U1", "2")]),
    # GND: TEMP and GND into the exposed pad; R1/C1 returns to pin 3; C2 to a via
    ("GND", "F", GND_W, [("U1", "1"), (9.0, 7.345), (9.0, 8.0)]),
    ("GND", "F", GND_W, [("U1", "3"), (9.2, 9.885)]),
    ("GND", "F", PWR, [("R1", "2"), (3.775, 9.885), ("C1", "2")]),
    ("GND", "F", PWR, [("U1", "3"), (3.775, 9.885)]),
    ("GND", "F", PWR, [("C2", "2"), (16.9, 11.0)]),
]
VIAS = {
    "/VIN": [(5.6, 7.1), (6.2, 11.155)],
    "/BAT+": [(13.85, 5.0), (13.85, 7.345), (13.85, 11.155)],
    "/SOL2": [(2.7, 5.1), (5.275, SOLAR_ROW_Y)],
    "/SOL3": [(17.6, 5.1), (14.725, SOLAR_ROW_Y)],
    # Two vias in the shared panel return; one for BAT- (its F.Cu pour island left of Q1) and two
    # by Q1's gate for OUT- and the gate; C2's return; six thermal vias in U1's exposed pad
    "GND": [(9.6, SOLAR_ROW_Y), (10.4, SOLAR_ROW_Y), (4.8, 4.8), (10.3, 5.7), (11.1, 5.7), (16.9, 11.0)]
    + [(x, y) for x in (9.4, 10.6) for y in (8.15, 9.25, 10.35)],
}

# Silkscreen: pair names under the top row, panel names over the solar row at the bottom edge.
LABELS = [("-BAT+", 6.0, 2.7), ("SW", 10.0, 2.7), ("+OUT-", 14.0, 2.7),
          ("S1+", 1.4, H - 2.58), ("S2+", 5.275, H - 2.58), ("GND", 10.0, H - 2.58), ("S3+", 14.725, H - 2.58), ("S4+", 18.6, H - 2.58)]
LABEL_TEXT = 0.8
# Back: the version between the holes and the name in the full-width band below them (clear of
# the vias at y 4.8-5.7).
BACK_TEXT = [("JaisorGadgets v2.0", 0.9, TOP_ROW_Y), ("SNAP Mini Power Controller", 0.8, 3.8)]  # text, height, y


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


def add_hole_keepout(board, cx, cy):
    """Rule area on both copper layers: no pour, tracks or vias under a screw head or standoff."""
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    n = 24
    for i in range(n):
        a = 2 * math.pi * i / n
        z.AppendCorner(pt(cx + HOLE_KEEPOUT * math.cos(a), cy + HOLE_KEEPOUT * math.sin(a)), -1)
    board.Add(z)


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
    tb.SetComment(0, "4 solar inputs -> CN3163 -> Q1 -> battery; switch -> load. 20 x 15 mm")

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
    for ref in ("H1", "H2"):
        add_hole_keepout(board, *PLACEMENT[ref][:2])

    for text, x, y in LABELS:
        silk_text(board, text, x, y, LABEL_TEXT, thickness=0.12)
    # Back: module ID, shrunk if needed to stay clear of the holes (0.3 mm margin).
    # A line entirely below the holes may use the board width less 1 mm a side.
    for text, height, y in BACK_TEXT:
        t = silk_text(board, text, W / 2, y, height, layer=pcbnew.B_SilkS, thickness=0.1)
        width = pcbnew.ToMM(t.GetEffectiveTextShape().BBox().GetWidth())
        beside_holes = abs(y - HOLE_XY) < HOLE_R + 0.3 + height / 2
        room = W - 2 * (HOLE_XY + HOLE_R + 0.3) if beside_holes else W - 2 * 1.0
        if width > room:
            s = height * room / width
            t.SetTextSize(pcbnew.VECTOR2I(mm(s), mm(s)))

    edge_outline(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb_path, board)
    print(f"board {W} x {H} mm, {len(fps)} footprints, {board.GetNetCount()} nets, "
          f"{sum(len(v) for v in VIAS.values())} vias, {len(zones)} GND zones")
    for ref in ("U1", "R1", "C1", "C2", "D1", "R2", "D2", "R3", "D3", "D4", "D5", "D6", "JP1", "J4", "Q1"):
        print(ref, {p.GetNumber(): tuple(round(v, 3) for v in pad_xy(ref, p.GetNumber())) for p in fps[ref].Pads() if p.GetNumber()})


main()
