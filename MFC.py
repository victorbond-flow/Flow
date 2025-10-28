"""
MFC.py
Skeleton code for the Bronkhorst EL-Flow Prestige (RS-232 / ProPar)
"""
import struct
from typing import Optional
import serial
import time


class MFC:
""" Need a good docstring """ 
    def __init__(self, port, baud=38400, timeout=1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

    # -----------------------------------------------------------
    # Connection handling
    # -----------------------------------------------------------
    def connect(self):
        """Open the serial connection."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )
            time.sleep(0.05)
            print(f"[MFC] Connected on {self.port} @ {self.baud} baud.")
        except Exception as e:
            print(f"[MFC] Connection failed: {e}")

    def disconnect(self):
        """Close the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[MFC] Disconnected.")
        self.ser = None

    # -----------------------------------------------------------
    # Low-level send / receive
    # -----------------------------------------------------------
    def send(self, data):
        """Send raw bytes or ASCII command and return raw reply."""
        if not self.ser or not self.ser.is_open:
            print("[MFC] Port not open.")
            return None

        if isinstance(data, str):
            data = data.encode('ascii')

        try:
            self.ser.reset_input_buffer()
            self.ser.write(data)
            time.sleep(0.05)
            reply = self.ser.read(128)
            return reply
        except Exception as e:
            print(f"[MFC] Send failed: {e}")
            return None

    # -----------------------------------------------------------
    # Helper commands
    # -----------------------------------------------------------
    def id_query(self):
        reply = self.send("ID\r") 
        if not reply:
            return None
        try:
            return reply.decode('ascii', errors='replace').strip()
        except Exception:
            return reply.hex()

    def read_raw(self):
        """Read any available bytes (useful for debugging)."""
        if not self.ser or not self.ser.is_open:
            print("[MFC] Port not open.")
            return b""
        return self.ser.read(128)

    def read_flow(self):
        """Return the measured flow in raw units (0..32000) or parsed value."""
        try:
            from parameters import PARAMS
            pid = PARAMS["measure"]["id"]
        except Exception:
            pid = 0x0020
        cmd = self.build_read_command(pid)
        raw = self.send(cmd)
        ok, val = self.interpret_response(raw, param_name="measure")
        return val if ok else raw

    def set_flow(self, percent_or_raw):
        """
        Accepts either percentage (0..100) or already-converted raw (0..32000).
        If percent provided as float <= 100, converts to raw scale and writes.
        """
        try:
            from parameters import PARAMS
            pid = PARAMS["setpoint"]["id"]
        except Exception:
            pid = 0x0021

        # convert percent -> raw if needed
        if isinstance(percent_or_raw, (int, float)) and percent_or_raw <= 100:
            raw_value = int(max(0, min(100.0, float(percent_or_raw))) * 32000 / 100.0)
        else:
            raw_value = int(percent_or_raw)

        cmd = self.build_write_command(pid, raw_value)
        reply = self.send(cmd)
        ok, val = self.interpret_response(reply, param_name="setpoint")
        return ok, val

    # ----------------------------------------------------------
    # ProPar command builder
    # ---------------------------------------------------------

    def build_read_command(self, param_id, address=1):
        """
        Build a ProPar read command for the given parameter ID.
        @param param_id: integer, e.g. 0x0020 for measure
        @param address: node address (default = 1)
        """
        # '@' = start, 'R' = read, 4-digit hex param, '\r' = end
        cmd = f"@{address:03d}R{param_id:04X}\r"
        return cmd.encode('ascii')

    def build_write_command(self, param_id, value, address=1):
        """
        Build a ProPar write command (basic ASCII version).
        Value should be an int or float.
        """
        # '@001W0021=12345\r' would set parameter 0x0021 (setpoint)
        cmd = f"@{address:03d}W{param_id:04X}={value}\r"
        return cmd.encode('ascii')


    # ----------------------------------------------------------
    # Response interpreting
    # ----------------------------------------------------------

    def interpret_response(self, raw: bytes, param_name: Optional[str] = None):
        """
        Lightweight, defensive parser for ProPar replies.
        - Tries ASCII decoding first (human-friendly devices often return ASCII).
        - If binary frames (STX/ETX) are used, it will extract payload and decode
          according to the type in parameters.PARAMS when param_name is provided.
        Returns: (success, value_or_raw)
        """
        # quick empty check
        if not raw:
            return False, None

        # try ASCII decode path first
        try:
            text = raw.decode('ascii', errors='replace').strip()
            # common ASCII reply patterns: echo, "OK", "VALUE", "@001 ...", or just numbers
            # try to extract a number directly
            import re
            m = re.search(r"([-+]?\d*\.\d+|[-+]?\d+)", text)
            if m:
                num = m.group(0)
                # prefer float if decimal point present
                if '.' in num:
                    return True, float(num)
                else:
                    return True, int(num)
            # if non-numeric ascii, return the stripped text
            return True, text
        except Exception:
            pass

        # If we reach here, raw wasn't parseable as ascii -> maybe a binary ProPar frame
        # detect STX/ETX style frame: STX(0x02) ... ETX(0x03) BCC
        if raw[0] == 0x02 and 0x03 in raw:
            try:
                start = 0
                etx_index = raw.index(0x03)
                payload = raw[start + 1:etx_index]  # bytes between STX and ETX
                # payload format varies; if caller gave param_name we can decode by type
                if param_name:
                    try:
                        from parameters import PARAMS
                        p = PARAMS.get(param_name)
                    except Exception:
                        p = None

                    if p:
                        ptype = p.get("type")
                        # common patterns:
                        if ptype == "uint16":
                            # payload might be the data directly or include header; try last 2 bytes
                            if len(payload) >= 2:
                                val = int.from_bytes(payload[-2:], byteorder='big', signed=False)
                                return True, val
                        elif ptype == "float":
                            # find any 4-byte window that produces a sane float
                            if len(payload) >= 4:
                                # assume MSB-first float (per manual)
                                val = struct.unpack(">f", payload[-4:])[0]
                                return True, val
                        elif ptype == "string":
                            try:
                                s = payload.decode('ascii', errors='replace').strip()
                                return True, s
                            except Exception:
                                pass
                # fallback: return raw payload hex
                return True, payload.hex()
            except Exception:
                return False, raw.hex()

        # final fallback: return raw as hex
        return False, raw.hex()
    



















