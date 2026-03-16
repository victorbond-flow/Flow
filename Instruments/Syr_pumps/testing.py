# testing.py

import crc16  # your crc16.py

# ---------------------------
# Command formatting & response parsing
# ---------------------------
def format_command(address, command):
    if address > 99:
        raise ValueError("Invalid Address")
    command = f"{address:02d}{command}"
    length = len(command) + 4  # length byte + CRC + termination
    crc_val = crc16.crc16xmodem(command.encode())
    crc_bytes = crc_val.to_bytes(2, "big")
    # return as a string including CRC for testing
    return f"{chr(length)}{command}{crc_bytes.decode('latin1')}"

def interpret_response(response, basic=False):
    if len(response) == 0:
        raise ValueError("Empty response")
    if basic:
        address = int(response[0:2])
        status = response[2]
        msg = response[3:]
    else:
        msg = response[:-2]
        crc = int.from_bytes(response[-2:].encode('latin1'), "big")
        if crc != crc16.crc16xmodem(msg.encode()):
            raise ValueError("CRC mismatch")
        address = int(msg[0:2])
        status = msg[2]
        msg = msg[3:]
    return address, status, msg

# ---------------------------
# Quick test
# ---------------------------
if __name__ == "__main__":
    cmd_text = "SAF0"
    formatted = format_command(0, cmd_text)
    print("Formatted command:", formatted)

    # simulate a fake basic-mode response
    response = "00SOC"  # address 00, status S, message OC
    addr, stat, msg = interpret_response(response, basic=True)
    print("Parsed response:", addr, stat, msg)

    # CRC test
    crc_val = crc16.crc16xmodem(b"SAF0")
    print("CRC16 of 'SAF0':", hex(crc_val))
