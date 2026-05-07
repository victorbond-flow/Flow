# ---------------------------------------------------------------------
# Parameter definitions for Bronkhorst EL-FLOW Prestige (RS-232 ProPar)
# ---------------------------------------------------------------------
# Each entry defines:
#   - name: human-readable identifier
#   - id:   ProPar / Modbus register (hexadecimal or decimal)
#   - type: data type (uint16, float, string, etc.)
#   - rw:   access type ('R' = read, 'W' = write, 'RW' = read/write)
#   - desc: brief description
#
# Example access pattern in MFC.py:
#   from parameters import PARAMS
#   PARAMS["measure"]["id"]  -> 0x0020
# ---------------------------------------------------------------------

PARAMS = {"""
need a docstring
"""
PARAMS = {
    "measure":   {"id": 0x0020, "type": "uint16", "desc": "Measured flow (0..32000 = 0..100%)"},
    "setpoint":  {"id": 0x0021, "type": "uint16", "desc": "Setpoint (0..32000 = 0..100%)"},
    "temperature":{"id": 0xA138, "type": "float",  "desc": "Internal temperature (°C)"},
    "pressure":  {"id": 0xA140, "type": "float",  "desc": "Pressure (bar)"},
    "serial_number": {"id": 0xF118, "type": "string", "rw": "R", "desc": "Instrument serial number."},
}
