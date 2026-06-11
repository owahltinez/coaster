#!/usr/bin/env python3
"""Turn design.py into the KiCad board.

    python generate.py        # writes coaster.kicad_pcb (zones filled)

design.py is the circuit (the source of truth); this file builds the board from
it with KiCad's pcbnew python API and validates connectivity. There is no
schematic: JLCPCB doesn't need one (it takes Gerbers + BOM + CPL), and design.py
already documents the circuit, so a derived schematic would buy nothing.

Zone filling runs as a child process (filling in the same process that built the
board segfaults in this pcbnew binding), so generate.py re-execs itself with
"fill" at the end.
"""
import os
import sys
import subprocess

import pcbnew
from pcbnew import VECTOR2I, FromMM

import design

# KiCad's stock footprint libraries: Linux package path or the macOS bundle.
SYS_FP_CANDIDATES = [
    "/usr/share/kicad/footprints",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
]
SYS_FP = next((p for p in SYS_FP_CANDIDATES if os.path.isdir(p)), SYS_FP_CANDIDATES[0])

# Fixed seed for KiCad's UUID generator. Every board item (footprints, pads,
# tracks, vias, zones, text) gets a fresh UUID at construction, and KiCad
# serializes items in UUID order -- so without a fixed seed each regeneration
# rewrites every UUID and reshuffles the file, producing a huge no-op diff.
# Seeding before we build anything makes the UUID sequence (and thus the file)
# byte-stable across runs as long as the design and build order are unchanged.
UUID_SEED = 0xC0A57E12


def fp_lib_path(footprint):
    """Resolve a 'lib:name' footprint id to (library_dir, name)."""
    lib, name = footprint.split(":")
    libdir = "./coaster.pretty" if lib == "coaster" else f"{SYS_FP}/{lib}.pretty"
    return libdir, name


def build_board():
    board = pcbnew.NewBoard("coaster.kicad_pcb")

    def mm(x, y):
        return VECTOR2I(FromMM(x), FromMM(y))

    netmap = {}
    for name in design.NETS:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        netmap[name] = n

    # 50x50mm outline
    for (x1, y1), (x2, y2) in [((0, 0), (50, 0)), ((50, 0), (50, 50)),
                               ((50, 50), (0, 50)), ((0, 50), (0, 0))]:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(mm(x1, y1))
        seg.SetEnd(mm(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(FromMM(0.1))
        board.Add(seg)

    pad_net = {(ref, pin): net for net, conns in design.NETS.items() for ref, pin in conns}

    fps = {}
    for ref, (x, y, rot) in design.PLACEMENT.items():
        libdir, name = fp_lib_path(design.PARTS[ref].footprint)
        fp = pcbnew.FootprintLoad(libdir, name)
        assert fp, f"footprint not found: {design.PARTS[ref].footprint}"
        fp.SetReference(ref)
        fp.SetValue(design.PARTS[ref].value)
        fp.SetPosition(mm(x, y))
        fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        for pad in fp.Pads():
            net = pad_net.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(netmap[net])
        board.Add(fp)
        fps[ref] = fp

    validate(fps)

    def pad_pos(ref, num):
        for pad in fps[ref].Pads():
            if pad.GetNumber() == num:
                p = pad.GetPosition()
                return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
        raise KeyError((ref, num))

    def track(net, pts, width=0.3, layer=pcbnew.F_Cu):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(mm(x1, y1))
            t.SetEnd(mm(x2, y2))
            t.SetWidth(FromMM(width))
            t.SetLayer(layer)
            t.SetNet(netmap[net])
            board.Add(t)

    def via(net, x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(mm(x, y))
        v.SetDrill(FromMM(0.3))
        v.SetWidth(pcbnew.F_Cu, FromMM(0.6))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(netmap[net])
        board.Add(v)

    # LED_K octagon: cathode pads are the cardinal vertices, diagonals bulge to
    # clear the button courtyard; then a north-west exit to Q1 drain.
    kN, kE, kS, kW = (pad_pos("L1", "1"), pad_pos("L2", "1"),
                      pad_pos("L3", "1"), pad_pos("L4", "1"))
    dNE, dSE, dSW, dNW = (29.38, 20.62), (29.38, 29.38), (20.62, 29.38), (20.62, 20.62)
    track("LED_K", [kN, dNE, kE, dSE, kS, dSW, kW, dNW, kN], 0.3)
    qd = pad_pos("Q1", "3")
    track("LED_K", [dNW, (19.5, 16.0), (19.5, 9.5), (qd[0], 9.5), qd], 0.3)

    # LED anode legs: short radial track resistor pad2 -> LED pad2
    for i, led in enumerate(("L1", "L2", "L3", "L4"), 1):
        track(f"LED_A{i}", [pad_pos(f"R{i}", "2"), pad_pos(led, "2")], 0.3)

    # LED_PWM: U1.7 below the pin row into Q1 gate; R5 gate-pulldown tap
    u7, qg, r5 = pad_pos("U1", "7"), pad_pos("Q1", "1"), pad_pos("R5", "1")
    track("LED_PWM", [u7, (u7[0], 16.2), (13.5, 16.2), (13.5, qg[1]), qg], 0.3)
    track("LED_PWM", [r5, (14.8, r5[1]), (14.8, qg[1]), qg], 0.3)

    # BUTTON: U1.2 -> C3 -> B.Cu diagonal under the LED ring to SW1's pads
    u2, c3 = pad_pos("U1", "2"), pad_pos("C3", "1")
    track("BUTTON", [u2, (u2[0], 7.0), c3], 0.3)
    track("BUTTON", [c3, (c3[0], 6.0), (15.5, 6.0)], 0.3)
    via("BUTTON", 15.5, 6.0)
    track("BUTTON", [(15.5, 6.0), (20.5, 9.0), (21.7, 21.6)], 0.3, pcbnew.B_Cu)
    via("BUTTON", 21.7, 21.6)
    track("BUTTON", [(21.7, 21.6), (21.7, 23.15)], 0.3)
    track("BUTTON", [(21.7, 21.6), (28.3, 21.6), (28.3, 23.15)], 0.3)

    # UPDI: stub south of U1.6, then B.Cu around the edge to J1 (through-hole)
    u6, j1 = pad_pos("U1", "6"), pad_pos("J1", "1")
    track("UPDI", [u6, (u6[0], 17.2)], 0.3)
    via("UPDI", u6[0], 17.2)
    track("UPDI", [(u6[0], 17.2), (6.0, 17.2), (6.0, 4.6), (8.0, 3.3), (42.0, 3.3), j1],
          0.3, pcbnew.B_Cu)

    # VCC: the pour distributes it; keep the decoupling path C1 -> U1.1 explicit
    c1, u1 = pad_pos("C1", "1"), pad_pos("U1", "1")
    track("VCC", [c1, (u1[0], c1[1]), u1], 0.5)

    # GND: a stitching via next to each SMD GND pad ties it to the B.Cu pour
    gnd_vias = {("C1", "2"): (14.3, 9.53), ("C2", "2"): (12.2, 22.0),
                ("U1", "8"): (11.8, 14.47), ("Q1", "2"): (18.5, 12.94),
                ("R5", "2"): (17.8, 15.68), ("C3", "2"): (14.27, 8.1),
                ("SW1", "2"): (21.7, 28.0)}
    for (ref, num), (vx, vy) in gnd_vias.items():
        track("GND", [pad_pos(ref, num), (vx, vy)], 0.4)
        via("GND", vx, vy)
    track("GND", [(28.3, 26.85), (28.3, 28.0)], 0.4)
    via("GND", 28.3, 28.0)

    # Battery return: the cell presses directly on BT1 pad 2 (bare copper), so
    # the stitching vias stay outside the 10mm contact circle -- drill dimples
    # or flux inside it would sit right at the contact surface. Spokes run from
    # the pad center out past the circle to vias into the B.Cu pour.
    bt = pad_pos("BT1", "2")
    for vx in (3.8, 16.2):
        track("GND", [bt, (vx, bt[1])], 0.4)
        via("GND", vx, bt[1])

    # Silkscreen: hide passive refdes (assembly uses the CPL file), keep U1/Q1,
    # label the programming pads, and run the documentation down the right margin.
    for ref in design.PLACEMENT:
        if ref not in ("U1", "Q1"):
            fps[ref].Reference().SetVisible(False)
    for ref, (rx, ry) in {"U1": (8.5, 18.3), "Q1": (19.9, 12.0)}.items():
        r = fps[ref].Reference()
        r.SetPosition(mm(rx, ry))
        r.SetTextSize(VECTOR2I(FromMM(0.9), FromMM(0.9)))
        r.SetTextThickness(FromMM(0.15))

    def silk(text, x, y, size=0.9, angle=0):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(mm(x, y))
        t.SetLayer(pcbnew.F_SilkS)
        if angle:
            t.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
        t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
        t.SetTextThickness(FromMM(max(0.13, size * 0.16)))
        board.Add(t)

    silk("UPDI", 42.0, 10.0, 0.8, angle=90)
    silk("VCC", 39.46, 9.7, 0.8, angle=90)
    silk("GND", 36.92, 9.7, 0.8, angle=90)
    silk("WAHLTINEZ BAR\nCOASTER v0.3", 25.0, 4.7, 1.2)
    silk("U1 ATTINY202   Q1 LED DRIVER", 40.4, 29, 0.8, angle=90)
    silk("PROG: UPDI 3-PIN, BATTERY OUT", 42.2, 29, 0.8, angle=90)
    silk("github.com/owahltinez/coaster", 44.0, 29, 0.8, angle=90)

    # Pours: B.Cu solid ground, F.Cu VCC. Build the outline inside the zone's
    # own poly set -- a Python-owned SHAPE_POLY_SET handed to SetOutline dangles
    # after GC and segfaults SaveBoard.
    for layer, net in [(pcbnew.B_Cu, "GND"), (pcbnew.F_Cu, "VCC")]:
        zone = pcbnew.ZONE(board)
        ol = zone.Outline()
        ol.NewOutline()
        for x, y in [(0.3, 0.3), (49.7, 0.3), (49.7, 49.7), (0.3, 49.7)]:
            ol.Append(FromMM(x), FromMM(y))
        zone.SetLayer(layer)
        zone.SetNet(netmap[net])
        zone.SetMinThickness(FromMM(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        board.Add(zone)

    pcbnew.SaveBoard("coaster.kicad_pcb", board)
    print("wrote coaster.kicad_pcb")


def validate(fps):
    """Connectivity sanity check against design.py (replaces schematic ERC).

    Catches the mistake ERC actually caught here -- a forgotten connection --
    directly from the source of truth: every component pad must be on a declared
    net or explicitly no-connect, and every net must reach at least two pads.
    DRC then checks the physical routing (shorts, unconnected copper).
    """
    nc = set(design.NO_CONNECT)
    errors = []
    for ref, fp in fps.items():
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num:  # mechanical pad (mounting hole)
                continue
            if not pad.GetNetname() and (ref, num) not in nc:
                errors.append(f"{ref}-{num} is not on any net and not in NO_CONNECT")
    for net, conns in design.NETS.items():
        on_board = [(r, p) for r, p in conns if r in fps]
        if len(on_board) < 2:
            errors.append(f"net {net} reaches < 2 pads on the board")
    if errors:
        raise SystemExit("connectivity validation failed:\n  " + "\n  ".join(errors))
    print(f"validated: {len(design.NETS)} nets, all pads connected or no-connect")


def fill_zones():
    board = pcbnew.LoadBoard("coaster.kicad_pcb")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard("coaster.kicad_pcb", board)
    print("filled zones")


if __name__ == "__main__":
    if sys.argv[1:] == ["fill"]:
        # Distinct seed from the build pass so any UUIDs the fill creates can't
        # collide with the board items already written by the parent process.
        pcbnew.KIID.SeedGenerator(UUID_SEED + 1)
        fill_zones()
    else:
        pcbnew.KIID.SeedGenerator(UUID_SEED)
        build_board()
        # fill in a child process (see module docstring)
        subprocess.run([sys.executable, __file__, "fill"], check=True)
