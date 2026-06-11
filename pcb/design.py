"""The coaster v0.3 circuit, as data.

This is the file a human reads or edits to understand or change the design;
generate.py turns it into the KiCad board. Connectivity is defined ONCE here
(NETS), and the board is built and verified directly against it. There is no
schematic: JLCPCB takes Gerbers + BOM + CPL, and this file already documents
the circuit, so a derived schematic would add nothing.

Mechanical constraints (from the manufactured v0.2 board): 50x50mm outline,
button SW1 dead-center under the shell flexure, LEDs ringing it at 6mm radius,
3mm mounting holes in all four corners.
"""
from collections import namedtuple

Part = namedtuple("Part", "footprint value")

# Footprints prefixed "coaster:" come from the local coaster.pretty library (pad
# geometry extracted from the v0.2 board); the rest are KiCad's own libraries.
PARTS = {
    "U1":  Part("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "ATtiny402-SSN"),
    "Q1":  Part("Package_TO_SOT_SMD:SOT-23", "AO3400A"),
    "BT1": Part("coaster:MY-2016-02", "CR2016"),
    "SW1": Part("coaster:TS-1187A", "TS-1187A-B-A-B"),
    "J1":  Part("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "UPDI"),
    "C1":  Part("Capacitor_SMD:C_0603_1608Metric", "100nF"),
    "C2":  Part("Capacitor_SMD:C_0805_2012Metric", "22uF"),
    "C3":  Part("Capacitor_SMD:C_0603_1608Metric", "100nF"),
    "R1":  Part("Resistor_SMD:R_0603_1608Metric", "150"),
    "R2":  Part("Resistor_SMD:R_0603_1608Metric", "150"),
    "R3":  Part("Resistor_SMD:R_0603_1608Metric", "150"),
    "R4":  Part("Resistor_SMD:R_0603_1608Metric", "150"),
    "R5":  Part("Resistor_SMD:R_0603_1608Metric", "100k"),
    "L1":  Part("LED_SMD:LED_0603_1608Metric", "KT-0603W"),
    "L2":  Part("LED_SMD:LED_0603_1608Metric", "KT-0603W"),
    "L3":  Part("LED_SMD:LED_0603_1608Metric", "KT-0603W"),
    "L4":  Part("LED_SMD:LED_0603_1608Metric", "KT-0603W"),
    "H1":  Part("MountingHole:MountingHole_3mm", "3mm"),
    "H2":  Part("MountingHole:MountingHole_3mm", "3mm"),
    "H3":  Part("MountingHole:MountingHole_3mm", "3mm"),
    "H4":  Part("MountingHole:MountingHole_3mm", "3mm"),
}

# The circuit: each net lists the (ref, pad) it connects. Single source of truth.
#   VCC ---[R1..R4 150R]--->|LED|--- LED_K --- Q1 drain ... Q1 source = GND
#   PA3 (LED_PWM) -> Q1 gate, with R5 gate pulldown to GND
#   button SW1 -> PA6 (BUTTON), debounced by C3; wakes the MCU
#   UPDI single-wire programming on PA0
NETS = {
    "VCC":     [("BT1", "1"), ("C1", "1"), ("C2", "1"), ("U1", "1"),
                ("R1", "1"), ("R2", "1"), ("R3", "1"), ("R4", "1"), ("J1", "2")],
    "GND":     [("BT1", "2"), ("C1", "2"), ("C2", "2"), ("U1", "8"), ("Q1", "2"),
                ("SW1", "2"), ("C3", "2"), ("R5", "2"), ("J1", "3")],
    "LED_PWM": [("U1", "7"), ("Q1", "1"), ("R5", "1")],
    "LED_K":   [("Q1", "3"), ("L1", "1"), ("L2", "1"), ("L3", "1"), ("L4", "1")],
    "LED_A1":  [("R1", "2"), ("L1", "2")],
    "LED_A2":  [("R2", "2"), ("L2", "2")],
    "LED_A3":  [("R3", "2"), ("L3", "2")],
    "LED_A4":  [("R4", "2"), ("L4", "2")],
    "BUTTON":  [("U1", "2"), ("SW1", "1"), ("C3", "1")],
    "UPDI":    [("U1", "6"), ("J1", "1")],
}

# U1 pins left unconnected (PA1, PA2, PA7). Declared so the connectivity check
# knows they are intentional, not forgotten.
NO_CONNECT = [("U1", "3"), ("U1", "4"), ("U1", "5")]

# Where each part sits on the PCB: (x_mm, y_mm, rotation_deg), origin top-left.
# LEDs ring the button (center 25,25) at 6mm; resistors at 10.5mm. LED pad1 is
# the cathode and faces inward; resistor pad2 (anode) faces its LED.
PLACEMENT = {
    "SW1": (25, 25, 0),
    "L1": (25, 19, 90),    "L2": (31, 25, 0),     "L3": (25, 31, 270),  "L4": (19, 25, 180),
    "R1": (25, 14.5, 270), "R2": (35.5, 25, 180), "R3": (25, 35.5, 90), "R4": (14.5, 25, 0),
    "U1": (8.5, 12, 270),
    "C1": (12.4, 9.53, 0),
    "Q1": (16.5, 12, 90),
    "R5": (16.5, 16.5, 90),
    "C2": (10, 22, 0),
    "C3": (13.5, 7.0, 0),
    "J1": (42, 5, 270),
    "BT1": (10, 36, 0),
    "H1": (3, 3, 0), "H2": (3, 47, 0), "H3": (47, 3, 0), "H4": (47, 47, 0),
}
