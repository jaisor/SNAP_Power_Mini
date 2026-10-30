# Builds the whole MiniPDB board from the schematic netlist: footprints placed and linked to
# their symbols, the BAT+ bridge on F.Cu, VOUT and GND split planes on B.Cu with via-in-pad
# transitions, silkscreen, and a square-cornered 20 x 10 mm outline (V-score panel friendly). Run with KiCad's Python:
#   "C:\Program Files\KiCad\10.0\bin\python.exe" tools/build-pcb.py <netlist.xml> [project dir, default: repo root]
# Netlist: kicad-cli sch export netlist --format kicadxml -o output/net.xml MiniPDB.kicad_sch
#
# Copper plan (pads 2.9 x 3.6 mm, + row on top, - row below):
#   F.Cu  J1.1 BAT+ ==== J2.1           J3.1 VOUT        B.Cu  [GND ][VOUT zone under J2 top,
#         J1.2 GND       J2.2           J3.2 GND               [    ][ J2.2 top half and J3.1 ]
#                                                              [GND strip under J2.2, J1.2, J3.2]
# J2.2 -> J3.1 (VOUT) and J1.2 -> J3.2 (GND) cross under the switch pads on B.Cu: VOUT takes
# the top of J2.2, GND runs along the bottom edge.
import os
import sys
import xml.etree.ElementTree as ET

import pcbnew

FPDIR = "C:/Program Files/KiCad/10.0/share/kicad/footprints"
NAME = "MiniPDB"
ORIGIN = (100.0, 100.0)  # board top-left in the editor, mm
W, H = 20.0, 10.0  # board size, mm
CORNER = 0.0  # outline corner radius, mm; 0 = sharp corners so panels can be V-scored
HOLE_INSET = 2.3  # M2 hole centre distance from the short edges, mm
ZONE_X = (4.8, 15.2)  # B.Cu planes stay clear of the M2 screw heads / standoffs (hex 4 mm)
ZONE_CLEAR = 0.3

# ref: (x, y, rotation) of the footprint origin, mm from the board's top-left corner.
PLACEMENT = {
    "H1": (HOLE_INSET, H / 2, 0),
    "H2": (W - HOLE_INSET, H / 2, 0),
    "J1": (6.5, H / 2, 0),  # BATTERY: 1 = BAT+ (top), 2 = GND
    "J2": (10.0, H / 2, 0),  # SWITCH:  1 = BAT+ (top), 2 = VOUT
    "J3": (13.5, H / 2, 0),  # LOAD:    1 = VOUT (top), 2 = GND
}
# F.Cu bridge between the battery + and switch pads (round ends stay inside the pads).
BRIDGES = [("/BAT+", (7.0, 2.5), (9.5, 2.5), 3.0)]
VIA = (0.8, 0.4)  # diameter, drill
VIAS = {
    "/VOUT": [(x, 6.3) for x in (9.0, 10.0, 11.0)]  # J2.2, top half (the GND strip passes under the rest)
    + [(x, y) for x in (12.6, 13.5, 14.4) for y in (1.4, 2.6)],  # J3.1
    "GND": [(x, y) for x in (5.6, 6.5, 7.4) for y in (7.1, 8.6)]  # J1.2
    + [(x, y) for x in (12.6, 13.5, 14.4) for y in (7.1, 8.6)],  # J3.2
}
# Vias sit toward the outer edges of their pads, leaving y 3.0-5.9 free on the back for BACK_TEXT.
# B.Cu zones: VOUT (priority 1) over the J2/J3 top area; GND (priority 0) fills the rest.
VOUT_ZONE = [(8.3, 0.5), (ZONE_X[1], 0.5), (ZONE_X[1], 5.0), (11.9, 5.0), (11.9, 6.9), (8.3, 6.9)]
GND_ZONE = [(ZONE_X[0], 0.5), (ZONE_X[1], 0.5), (ZONE_X[1], H - 0.5), (ZONE_X[0], H - 0.5)]

# Silkscreen: column names in the gap between the pad rows, +/- beside each row at both ends.
COLUMN_LABELS = {"J1": "BAT", "J2": "SW", "J3": "OUT"}
LABEL_TEXT = 0.8
ROW_MARKS = [("+", 1.55), ("-", H - 1.55)]
ROW_MARK_TEXT = 1.2
BACK_TEXT = [("Mini PDB v1.0", 1.0, 3.9), ("by JaisorGadgets", 0.8, 5.15)]  # text, height, y


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


def add_zone(board, layer, net, corners, priority):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(net)
    for x, y in corners:
        z.AppendCorner(pt(x, y), -1)
    z.SetLocalClearance(mm(ZONE_CLEAR))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetAssignedPriority(priority)
    board.Add(z)
    return z


def main():
    netfile = sys.argv[1]
    proj = sys.argv[2] if len(sys.argv) > 2 else "."
    pcb_path = os.path.join(proj, NAME + ".kicad_pcb")
    root = ET.parse(netfile).getroot()

    board = pcbnew.NewBoard(pcb_path)
    tb = board.GetTitleBlock()
    tb.SetTitle("Mini PDB")
    tb.SetRevision("0.1")
    tb.SetDate("2026-10-30")
    tb.SetComment(0, "Battery -> switch -> load wire-pad distribution board, 20 x 10 mm, 2x M2")

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
        if ref.startswith("H"):
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

    for name, a, b, width in BRIDGES:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(mm(width))
        t.SetLayer(pcbnew.F_Cu)
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
    zones = [add_zone(board, pcbnew.B_Cu, code["/VOUT"], VOUT_ZONE, 1),
             add_zone(board, pcbnew.B_Cu, code["GND"], GND_ZONE, 0)]

    for ref, text in COLUMN_LABELS.items():
        silk_text(board, text, PLACEMENT[ref][0], H / 2, LABEL_TEXT, thickness=0.12)
    for text, y in ROW_MARKS:
        for x in (HOLE_INSET, W - HOLE_INSET):
            silk_text(board, text, x, y, ROW_MARK_TEXT, thickness=0.2)
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
          f"{sum(len(v) for v in VIAS.values())} vias, {len(zones)} zones")


main()
