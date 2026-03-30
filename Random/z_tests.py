import socket
import xml.etree.ElementTree as ET

IP = "192.168.1.101"  # replace with your Gilson's IP
ADMIN_PORT = 50185

# ----------------- Connect to admin -----------------
def get_session_port(ip, admin_port):
    message = "<Gilson><GilsonConnect>Gilson Ethernet Utility</GilsonConnect></Gilson>"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect((ip, admin_port))
        s.sendall(message.encode("ascii"))
        resp = s.recv(4096).decode("ascii")
    port = int(resp.split("<ParameterValue>")[2].split("</ParameterValue>")[0])
    return port

# ----------------- Connect to session -----------------
def open_session(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect((ip, port))
    return s

# ----------------- Send raw command -----------------
def send_command(sock, xml_payload):
    sock.sendall(xml_payload.encode("ascii"))
    buffer = b""
    import time
    start = time.time()
    while time.time() - start < 1.0:  # wait up to 1 sec
        try:
            sock.settimeout(0.05)
            part = sock.recv(8192)
            if part:
                buffer += part
            else:
                break
        except socket.timeout:
            continue
    return buffer.decode("ascii", errors="ignore")

# ----------------- Make XML for a command -----------------
def make_xml(command_name, parameters=None):
    param_xml = ""
    if parameters:
        param_xml = "<Parameters>"
        for k, v in parameters.items():
            param_xml += f"<Parameter><ParameterName>{k}</ParameterName><ParameterValue>{v}</ParameterValue></Parameter>"
        param_xml += "</Parameters>"
    xml = f"""
<Gilson>
  <CommandData>
    <Commands>
      <Command>
        <CommandType>Local</CommandType>
        <CommandInfo>
          <InstrumentInfo>
            <DeviceName>GX-27x</DeviceName>
            <DeviceId>35</DeviceId>
          </InstrumentInfo>
          <SequenceNumber>100</SequenceNumber>
          <Synchronize>True</Synchronize>
          <Selected>False</Selected>
          <CommandXML>
            <CommandName>{command_name}</CommandName>
            {param_xml}
          </CommandXML>
        </CommandInfo>
      </Command>
    </Commands>
  </CommandData>
</Gilson>
"""
    return xml.strip()

# ----------------- Quick parser for Z -----------------
def parse_z_full(xml_message):
    """
    Parse Z Position across multiple Message blocks in firmware response.
    Returns float Z position, or None if not found.
    """
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(f"<root>{xml_message}</root>")  # wrap in root to handle multiple top-level Message tags
        for rp in root.findall(".//ReturnParameter"):
            name = rp.findtext("ParameterName")
            value = rp.findtext("ParameterValue")
            if name == "Z Position" and value is not None:
                return float(value)
        # fallback: look in Parameter tags
        for p in root.findall(".//Parameter"):
            name = p.findtext("ParameterName")
            value = p.findtext("ParameterValue")
            if name == "Z Position" and value is not None:
                return float(value)
    except ET.ParseError:
        return None
    return None