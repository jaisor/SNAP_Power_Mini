# Builds the whole MiniPDB board from the schematic netlist: footprints placed and linked to
# their symbols, hand-placed tracks and vias, GND pours on both layers kept clear of the M2
# holes, silkscreen, and a square-cornered 20 x 12 mm outline (V-score panel friendly).
# Run with KiCad's Python:
#   "C:\Program Files\KiCad\10.0\bin\python.exe" tools/build-pcb.py <netlist.xml> [project dir, default: repo root]
# Netlist: kicad-cli sch export netlist --format kicadxml -o output/net.xml MiniPDB.kicad_sch
#
# Layout (top view). Top band: M2 holes and four wire-pad pairs, + row on top:
#   (H1)  SOL+ BAT+=SW_A  OUT+  (H2)      BAT+ = SW_A bridged on F.Cu
#         SOL- BAT- SW_B  OUT-            SOL- = BAT- bridged on F.Cu
# Bottom band: R1 (ISET) and C1 (VIN) left of U1 CN3163; right of it the status LEDs in two
# rows (D1 red + R2 on CHRG, D2 green + R3 on DONE, 0402) above C2 (BAT).
# B.Cu jumpers: SOL+ -> C1/VIN pin, BAT+ -> FB and BAT pins, SW_B -> OUT+.
# F.Cu: VIN to the LED resistors runs between the pad rows and the IC.
# No net carries more than 1 A: 0.4 mm power tracks, 0.3 mm vias.
import math
import os
import sys
import xml.etree.ElementTree as ET

import pcbnew

FPDIR = "C:/Program Files/KiCad/10.0/share/kicad/footprints"
NAME = "MiniPDB"
ORIGIN = (100.0, 100.0)  # board top-left in the editor, mm
W, H = 20.0, 12.0  # board size, mm
CORNER = 0.0  # outline corner radius, mm; 0 = sharp corners so panels can be V-scored
PAD_ROW_Y = 3.35  # centre line of the wire-pad pairs (pads at y -/+ 1.75)
HOLE_INSET = 2.3  # M2 hole centre distance from the short edges, mm
HOLE_KEEPOUT = 2.2  # no copper within this radius of a hole centre (screw head / standoff)
ZONE_CLEAR = 0.25

# ref: (x, y, rotation) of the footprint origin, mm from the board's top-left corner.
PLACEMENT = {
    "H1": (HOLE_INSET, PAD_ROW_Y, 0),
    "H2": (W - HOLE_INSET, PAD_ROW_Y, 0),
    "J4": (6.1, PAD_ROW_Y, 0),  # SOLAR:   1 = VIN (top), 2 = GND
    "J1": (8.7, PAD_ROW_Y, 0),  # BATTERY: 1 = BAT+ (top), 2 = GND
    "J2": (11.3, PAD_ROW_Y, 0),  # SWITCH:  1 = BAT+ (top), 2 = VOUT
    "J3": (13.9, PAD_ROW_Y, 0),  # LOAD:    1 = VOUT (top), 2 = GND
    "U1": (10.0, 9.25, 0),  # CN3163: pins 1-4 down the left (VIN = 4), 5-8 up the right (BAT = 5)
    "R1": (4.6, 8.615, 180),  # in line with ISET (pin 2); pad 1 toward the IC
    "C1": (4.7, 11.0, 180),  # VIN bypass next to pin 4; pad 1 toward the IC
    "C2": (15.3, 11.0, 0),  # BAT capacitor next to pin 5; pad 1 toward the IC
    "D1": (14.75, 8.4, 0),  # red, CHRG: cathode (pad 1) toward pin 7
    "R2": (16.7, 8.4, 0),
    "D2": (14.75, 9.6, 0),  # green, DONE: cathode (pad 1) toward pin 6
    "R3": (16.7, 9.6, 0),
}
PWR, SIG, GND_W = 0.4, 0.25, 0.3  # track widths, mm
VIA = (0.6, 0.3)  # diameter, drill
# Tracks: (net, layer, width, points). A point is (x, y) or (ref, pad) for that pad's centre.
TRACKS = [
    ("/BAT+", "F", 1.2, [("J1", "1"), ("J2", "1")]),
    ("GND", "F", 1.2, [("J4", "2"), ("J1", "2")]),
    # VIN: SOL+ -> B.Cu -> via between C1 and pin 4
    ("/VIN", "B", PWR, [(5.6, 2.1), (5.6, 10.55), (6.2, 11.155)]),
    ("/VIN", "F", PWR, [("C1", "1"), (6.2, 11.155), ("U1", "4")]),
    # VIN for the LEDs: via on the SOL+ jumper, along F.Cu above the IC, down through R2/R3
    ("/VIN", "F", SIG, [(5.6, 6.9), (5.8, 6.7), (17.21, 6.7), ("R2", "2"), ("R3", "2")]),
    # BAT+: BAT+ pad -> B.Cu under the pads and down beside the IC to vias at pins 8 and 5,
    # leaving F.Cu free for the CHRG/DONE tracks between them
    ("/BAT+", "B", PWR, [(8.2, 2.1), (8.2, 6.9), (13.85, 6.9), (13.85, 11.155)]),
    ("/BAT+", "F", PWR, [("U1", "8"), (13.85, 7.345)]),
    ("/BAT+", "F", PWR, [("U1", "5"), (13.85, 11.155), ("C2", "1")]),
    # Status LEDs: pin -> cathode, anode -> resistor -> VIN
    ("Net-(D1-K)", "F", SIG, [("U1", "7"), (13.7, 8.615), ("D1", "1")]),
    ("Net-(D2-K)", "F", SIG, [("U1", "6"), (13.7, 9.885), ("D2", "1")]),
    ("Net-(D1-A)", "F", SIG, [("D1", "2"), ("R2", "1")]),
    ("Net-(D2-A)", "F", SIG, [("D2", "2"), ("R3", "1")]),
    # VOUT: switch pad -> B.Cu -> load + pad
    ("/VOUT", "B", PWR, [(11.3, 4.55), (13.9, 2.15)]),
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
    "/VIN": [(5.6, 2.1), (5.6, 6.9), (6.2, 11.155)],
    "/BAT+": [(8.2, 2.1), (13.85, 7.345), (13.85, 11.155)],
    "/VOUT": [(11.3, 4.55), (13.9, 2.15)],
    # J1.2 and J3.2 to the B.Cu pour, C2's return, and six thermal vias in U1's exposed pad
    "GND": [(9.2, 4.6), (13.4, 4.6), (16.9, 11.0)]
    + [(x, y) for x in (9.4, 10.6) for y in (8.15, 9.25, 10.35)],
}

# Silkscreen: column names in the gap between the pad rows, +/- beside each row at both ends.
COLUMN_LABELS = {"J4": "SOL", "J1": "BAT", "J2": "SW", "J3": "OUT"}
LABEL_TEXT = 0.8
ROW_MARKS = [("+", 0.85, 0.8), ("-", 6.0, 1.0)]  # text, y, height
# Back: kept in the via-free bands at y 2.5-4.2 and 4.9-6.6.
BACK_TEXT = [("Mini PDB v2.0", 0.9, PAD_ROW_Y), ("by JaisorGadgets", 0.8, 5.65)]  # text, height, y


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
    tb.SetTitle("Mini PDB")
    tb.SetRevision("0.2")
    tb.SetDate("2026-10-30")
    tb.SetComment(0, "Solar -> CN3163 -> battery; battery -> switch -> load. Wire pads, 20 x 12 mm, 2x M2")

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

    for ref, text in COLUMN_LABELS.items():
        silk_text(board, text, PLACEMENT[ref][0], PAD_ROW_Y, LABEL_TEXT, thickness=0.12)
    for text, y, height in ROW_MARKS:
        for x in (HOLE_INSET, W - HOLE_INSET):
            silk_text(board, text, x, y, height, thickness=0.2)
    # Back: module ID, shrunk if needed to stay clear of the holes (2.2 mm, 0.3 mm margin).
    for text, height, y in BACK_TEXT:
        t = silk_text(board, text, W / 2, y, height, layer=pcbnew.B_SilkS, thickness=0.1)
        width = pcbnew.ToMM(t.GetEffectiveTextShape().BBox().GetWidth())
        room = W - 2 * (HOLE_INSET + 1.1 + 0.3)
        if width > room:
            s = height * room / width
            t.SetTextSize(pcbnew.VECTOR2I(mm(s), mm(s)))

    edge_outline(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb_path, board)
    print(f"board {W} x {H} mm, {len(fps)} footprints, {board.GetNetCount()} nets, "
          f"{sum(len(v) for v in VIAS.values())} vias, {len(zones)} GND zones")
    for ref in ("U1", "R1", "C1", "C2", "D1", "R2", "D2", "R3"):
        print(ref, {p.GetNumber(): tuple(round(v, 3) for v in pad_xy(ref, p.GetNumber())) for p in fps[ref].Pads() if p.GetNumber()})


main()
