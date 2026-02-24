import serial
import time
from Core.flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

class AL1000:
    """
    AL1000 Syringe Pump Driver

    This class talks to a WPI AL-1000 pump using its simple
    ASCII-based serial protocol.

    Goals of this upgraded version:
    - Always log the raw pump reply (useful for debugging).
    - Cleanly strip protocol wrappers (00S, 00A, 00W...).
    - Decode RAT, VOL, DIA, DIR, etc. into human-readable values.
    - Provide a unified parsing path so all I/O behaves consistently.
    """

    def __init__(self, port="COM2", baudrate=9600, device_address="@00", sleep_time=0.5, use_splat=True):
        self.port = port
        self.baudrate = baudrate
        self.device_address = device_address
        self.sleep_time = sleep_time
        self.ser = None
        self.use_splat = use_splat
    # -------------------------------------------------------------------------
    # Core methods
    # -------------------------------------------------------------------------
    @log_call
    def connect(self):
        """Open serial port and verify connection."""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=1
        )

        if self.ser.is_open:
            print(f"AL1000 pump connected on {self.port}")
        else:
            raise RuntimeError(f"Could not open port {self.port}")

    def command(self, code):
        """
        Low-level method:
        Sends <address>*<code> and returns the raw decoded string only.

        parse_response() is not performed here — this keeps this method
        backward compatible and purely “raw I/O”.
        """
        cmd_prefix = "*" if self.use_splat else ""
        full_cmd = f"{self.device_address}{cmd_prefix}{code}\r"
        self.ser.write(full_cmd.encode('ascii'))
        time.sleep(self.sleep_time)

        raw = self.ser.read(64)
        if not raw:
            print(f"Sent: {full_cmd.strip()} | Reply: <none>")
            return None

        # Strip STX / ETX if present
        if raw.startswith(b'\x02'):
            raw = raw[1:]
        if raw.endswith(b'\x03'):
            raw = raw[:-1]

        decoded = raw.decode('ascii', errors='replace').strip()

        print(f"Sent: {full_cmd.strip()}")
        return decoded

    # -------------------------------------------------------------------------
    # Unified parser
    # -------------------------------------------------------------------------
    def parse_response(self, code: str, resp: str):
        """
        Turn a raw response like '00S10.00ML' into:
        {
            "raw": "00S10.00ML",
            "payload": "10.00ML",
            "interpreted": {"volume": 10.00, "units": "mL"},
        }
        """

        if resp is None:
            return {"raw": None, "payload": None, "interpreted": {}}

        raw = resp.strip()

        # Strip the first 3 chars: 00S / 00A / 00W etc.
        if len(raw) >= 3:
            payload = raw[3:]
        else:
            payload = ""

        interpreted = self.decode_payload(code, payload)

        return {
            "raw": raw,
            "payload": payload,
            "interpreted": interpreted
        }

    # -------------------------------------------------------------------------
    # Decoders (structured + data-driven)
    # -------------------------------------------------------------------------
    def decode_payload(self, code, payload):
        """
        Dispatch table using command prefix (RAT, VOL, DIA, DIR).
        """
        key = code[:3] if code else ""

        decoders = {
            "RAT": self._decode_rate,
            "VOL": self._decode_volume,
            "DIA": self._decode_diameter,
            "DIR": self._decode_direction,
        }

        func = decoders.get(key)
        if func:
            return func(payload)

        # default fallback
        return {}

    def _decode_rate(self, payload):
        try:
            value = float(payload[:-2])
            return {"rate": value, "units": "mL/min"}
        except Exception:
            return {}

    def _decode_volume(self, payload):
        try:
            value = float(payload[:-2])
            return {"volume": value, "units": "mL"}
        except Exception:
            return {}

    def _decode_diameter(self, payload):
        try:
            value = float(payload)
            return {"diameter": value, "units": "mm"}
        except Exception:
            return {}

    def _decode_direction(self, payload):
        return {"direction": payload}

    # -------------------------------------------------------------------------
    # Response formatting
    # -------------------------------------------------------------------------
    def format_response(self, label: str, reply: dict) -> str:
        raw = reply.get("raw", "")
        interp = reply.get("interpreted", {})
    
        if raw == "00S" and not interp:
            human_readable = "Acknowledged"
            return f"{label}\nRaw reply: {raw}\nParsed reply: {human_readable}"
    
        if not interp:
            return f"{label}\nRaw reply: {raw}"
    
        segments = []
        for key, value in interp.items():
            pretty_key = key.capitalize()
            segments.append(f"{pretty_key} = {value}")
    
        interpreted_str = ", ".join(segments)
        return f"Raw reply: {raw}\nParsed reply: {interpreted_str}"



    # -------------------------------------------------------------------------
    # Send & parse helper
    # -------------------------------------------------------------------------
    def send_and_parse(self, code: str):
        cmd_prefix = "*" if self.use_splat else ""
        full_cmd = f"{self.device_address}{cmd_prefix}{code}\r"

        self.ser.write(full_cmd.encode("ascii"))
        time.sleep(self.sleep_time)

        raw_bytes = self.ser.read(64)
        if not raw_bytes:
            parsed = {"raw": None, "payload": None, "interpreted": {}}
            print(f"Sent: {full_cmd.strip()}\nRaw reply: <none>")
            return parsed

        if raw_bytes.startswith(b'\x02'):
            raw_bytes = raw_bytes[1:]
        if raw_bytes.endswith(b'\x03'):
            raw_bytes = raw_bytes[:-1]

        raw_str = raw_bytes.decode("ascii", errors="replace").strip()
        parsed = self.parse_response(code, raw_str)

        return parsed

    # -------------------------------------------------------------------------
    # High-level “get” wrappers
    # -------------------------------------------------------------------------
    def get_diameter(self, verbose=True):
        parsed = self.send_and_parse("DIA")
        if verbose:
            print(self.format_response("Diameter", parsed))
        return parsed
    
    def get_rate(self, verbose=True):
        parsed = self.send_and_parse("RAT")
        if verbose:
            print(self.format_response("Rate", parsed))
        return parsed
    
    def get_volume(self, verbose=True):
        parsed = self.send_and_parse("VOL")
        if verbose:
            print(self.format_response("Volume", parsed))
        return parsed
    
    def get_direction(self, verbose=True):
        parsed = self.send_and_parse("DIR")
        if verbose:
            print(self.format_response("Direction", parsed))
        return parsed


    # -------------------------------------------------------------------------
    # Set commands
    # -------------------------------------------------------------------------
    def set_diameter(self, dia, verbose=True):
        """
        Set the syringe diameter.
        Prints both raw and human-readable acknowledgement if verbose.
        """
        resp = self.command(f"DIA{dia}")
        if verbose:
            parsed = self.parse_response("DIA", resp)
            # Convert simple "00S" into 'Acknowledged'
            if resp == "00S":
                parsed["interpreted"] = {"Acknowledged": True}
            print(self.format_response("DIA", parsed))
        return resp
    
    def set_rate(self, rate, verbose=True):
        resp = self.command(f"RAT C {rate} MM")
        if verbose:
            parsed = self.parse_response("RAT", resp)
            if resp == "00S":
                parsed["interpreted"] = {"Acknowledged": True}
            print(self.format_response("RAT", parsed))
        return resp
    
    def set_volume(self, volume, verbose=True):
        resp = self.command(f"VOL{volume}")
        if verbose:
            parsed = self.parse_response("VOL", resp)
            if resp == "00S":
                parsed["interpreted"] = {"Acknowledged": True}
            print(self.format_response("VOL", parsed))
        return resp
    
    def set_direction(self, direction, verbose=True):
        resp = self.command(f"DIR{direction}")
        if verbose:
            parsed = self.parse_response("DIR", resp)
            if resp == "00S":
                parsed["interpreted"] = {"Acknowledged": True}
            print(self.format_response("DIR", parsed))
        return resp


    # -------------------------------------------------------------------------
    # Status reporting
    # -------------------------------------------------------------------------
    def get_status(self):
        """
        Return a full snapshot of the pump's current state:
        - rate, volume, direction, phase
        - all parsed into raw/payload/interpreted format
        Prints a human-readable summary.
        """
        # Parse everything, suppress intermediate printing
        phase_parsed = self.send_and_parse("PHN")
        rate_parsed  = self.get_rate(verbose=False)
        vol_parsed   = self.get_volume(verbose=False)
        dir_parsed   = self.get_direction(verbose=False)
    
        # Optionally extract a human-readable status from phase
        status = phase_parsed.get("interpreted", {}).get("phase", "Unknown")
    
        # Combine into a single dictionary snapshot
        status_snapshot = {
            "status": status,
            "phase": phase_parsed,
            "rate": rate_parsed,
            "volume": vol_parsed,
            "direction": dir_parsed
        }
    
        # Print a concise summary for notebooks
        print("\n--- Pump Status Snapshot ---")
        print(self.format_response("Phase", phase_parsed))
        print(self.format_response("Rate", rate_parsed))
        print(self.format_response("Volume", vol_parsed))
        print(self.format_response("Direction", dir_parsed))
        print("--- End of Snapshot ---\n")
    
        return status_snapshot



    # -------------------------------------------------------------------------
    # Program phases
    # -------------------------------------------------------------------------
    def select_phase(self, phase=1):
        return self.command(f"PHN{phase}")

    # -------------------------------------------------------------------------
    # Control
    # -------------------------------------------------------------------------
    def start(self):
        return self.command("RUN 1")

    def stop(self):
        return self.command("STP")

    # -------------------------------------------------------------------------
    # Prepare method
    # -------------------------------------------------------------------------
    def prepare(self, rate, volume, direction):
        """
        Prepare the AL1000 syringe pump for a run:
        - Set rate (mL/min)
        - Set volume (µL or mL, depending on firmware)
        - Set direction ('INF' or 'WDR')
        
        Uses the existing syringe diameter (assumed fixed).
        Raises RuntimeError if any command fails.
        """
    
        # Select phase 1 (no ack check needed)
        self.select_phase(1)
    
        # Set rate
        resp = self.set_rate(rate, verbose=False)
        if resp not in ("00S", "00P"):
            raise RuntimeError(f"Rate not acknowledged: {resp}")
    
        # Set volume
        resp = self.set_volume(volume, verbose=False)
        if resp not in ("00S", "00P"):
            raise RuntimeError(f"Volume not acknowledged: {resp}")
    
        # Set direction
        resp = self.set_direction(direction, verbose=False)
        if resp not in ("00S", "00P"):
            raise RuntimeError(f"Direction not acknowledged: {resp}")











    