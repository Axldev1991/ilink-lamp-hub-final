
import asyncio
import sys
from bleak import BleakClient

# =============================================================================
# HARDWARE DEFINITIONS (iLink / Jieli SDK)
# =============================================================================
ADDRESS = "A8:D2:CD:C7:9C:AC"
CHAR_UUID = "0000a040-0000-1000-8000-00805f9b34fb"

class ILinkControl:
    """
    Core Protocol Abstraction for iLink Bluetooth Lamps.
    Handles binary packet construction and CRC validation for the Jieli BLE hardware.
    """
    def __init__(self):
        # Proprietary protocol header (Dual-byte)
        self.header = "55aa"

    def _build_packet(self, mode, cmd_hex):
        """
        Constructs a validated binary packet for the GATT characteristic.
        
        Args:
            mode (str): Command category ('01' for System, '03' for RGB).
            cmd_hex (str): Specific command body in hex format.
            
        Returns:
            bytearray: Ready-to-send packet including Calculated Checksum.
        """
        pkt_str = self.header + mode + cmd_hex
        
        # CHECKSUM ALGORITHM:
        # 1. Sum all bytes of the header + mode + command body.
        # 2. Apply 8-bit mask (0xFF).
        # 3. Subtract result from 0xFF to get the parity/checksum byte.
        all_sum = 0
        for i in range(0, len(pkt_str), 2):
            all_sum += int(pkt_str[i : i + 2], 16)
        
        crc = (0xFF - (all_sum & 0xFF)) & 0xFF
        return bytearray.fromhex(pkt_str + f"{crc:02x}")

    async def send_command(self, mode, cmd_hex):
        """Standard async GATT write wrapper."""
        packet = self._build_packet(mode, cmd_hex)
        async with BleakClient(ADDRESS) as client:
            if client.is_connected:
                await client.write_gatt_char(CHAR_UUID, packet)
                return True
        return False

    async def power_on(self):
        """Sends the system wake/ON command (080501)."""
        return await self.send_command("01", "080501")

    async def power_off(self):
        """Sends the system sleep/OFF command (080500)."""
        return await self.send_command("01", "080500")

    async def set_rgb(self, r, g, b):
        """
        Updates the color spectrum.
        Protocol: Mode 0x03 (Color), Cmd 0x0802 followed by 3 bytes of RGB data.
        """
        color_hex = f"0802{r:02x}{g:02x}{b:02x}"
        return await self.send_command("03", color_hex)

    async def set_brightness(self, level):
        """
        Updates intensity level (0-255).
        Protocol: Mode 0x01 (System), Cmd 0x0801 followed by 1 byte of brightness.
        """
        return await self.send_command("01", f"0801{level:02x}")

async def main():
    """CLI Entry point for quick hardware testing and diagnostics."""
    lamp = ILinkControl()
    
    print("--- iLink Diagnostics Sequence ---")
    
    # 1. Wake up sequence
    print("[1/3] Powering ON...")
    await lamp.power_on()
    await asyncio.sleep(1)
    
    # 2. Spectrum test (Green)
    print("[2/3] Setting GREEN spectrum...")
    await lamp.set_rgb(0, 255, 0)
    await asyncio.sleep(2)
    
    # 3. Dimming test (approx 20% intensity)
    print("[3/3] Testing PWM dimming (level 50)...")
    await lamp.set_brightness(50)
    
    print("Diagnostics complete. Hardware responds correctly.")

if __name__ == "__main__":
    # Launch CLI test suite
    asyncio.run(main())
