
import tkinter as tk
from tkinter import colorchooser, ttk
import asyncio
import threading
import subprocess
import time
import math
from bleak import BleakClient

# --- CONFIGURACIÓN ---
BLE_ADDRESS = "A8:D2:CD:C7:9C:AC"
AUDIO_ADDRESS = "AC:9C:C7:CD:D2:A8"
CHAR_UUID = "0000a040-0000-1000-8000-00805f9b34fb"

# --- PALETA DE COLORES ---
BG_COLOR = "#0F0F0F"
ACCENT = "#00F5D4"
TEXT_COLOR = "#FFFFFF"
DIM_TEXT = "#777777"
RED_ACCENT = "#FF5D73"
GREEN_ACCENT = "#2ECC71"

class ILinkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("iLink Ultra Hub")
        self.root.geometry("400x780") # Más compacta sin el timer
        self.root.configure(bg=BG_COLOR)
        
        self.client = None
        self.queue = None
        self.last_slider_send = 0
        self.running = True
        self.rainbow_active = False 
        self.is_on = True 
        
        # Loop de Bluetooth en hilo separado
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

        self._setup_ui()
        self._setup_hotkeys()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main_async())

    async def _main_async(self):
        self.queue = asyncio.Queue()
        await self._connection_manager()

    # --- HOTKEYS ---
    def _setup_hotkeys(self):
        # Lámpara
        self.root.bind("<space>", lambda e: self.toggle_power())
        self.root.bind("1", lambda e: self.set_intensity_only(64))
        self.root.bind("2", lambda e: self.set_intensity_only(128))
        self.root.bind("3", lambda e: self.set_intensity_only(191))
        self.root.bind("4", lambda e: self.set_intensity_only(255))
        self.root.bind("<Up>", lambda e: self._adjust_brightness(15))
        self.root.bind("<Down>", lambda e: self._adjust_brightness(-15))
        
        # Bluetooth del Sistema
        self.root.bind("b", lambda e: self.bt_power_on()) # B = Bluetooth ON
        self.root.bind("n", lambda e: self.bt_power_off()) # N = No Bluetooth (OFF)

    def toggle_power(self):
        if self.is_on:
            self.run_cmd(("01", "080500"), True)
            self.is_on = False
        else:
            self.run_cmd(("01", "080501"), True)
            self.is_on = True

    def _adjust_brightness(self, delta):
        new_val = max(1, min(255, self.bright_slider.get() + delta))
        self.bright_slider.set(new_val)
        self.set_intensity_only(new_val)

    # --- LÓGICA BT ---
    def update_status(self, text, color=ACCENT):
        self.root.after(0, lambda: self.status_label.config(text=text, fg=color))

    async def _connection_manager(self):
        while self.running:
            if self.client is None or not self.client.is_connected:
                self.update_status("📡 BUSCANDO LÁMPARA...", "#F1C40F")
                try:
                    self.client = BleakClient(BLE_ADDRESS, timeout=5.0)
                    await self.client.connect()
                    self.update_status("🟢 CONECTADO", GREEN_ACCENT)
                except Exception:
                    self.update_status("🔴 SIN CONEXIÓN", RED_ACCENT)
                    await asyncio.sleep(2)
                    continue
            
            try:
                timeout = 0.05 if self.rainbow_active else 0.5
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                    if item is None: break
                    
                    while self.queue.qsize() > 0:
                        next_item = self.queue.get_nowait()
                        if next_item is None: self.running = False; item = None; break
                        if item[1].startswith('0801') and next_item[1].startswith('0801'):
                            item = next_item
                        else:
                            self.queue.put_nowait(next_item); break

                    if item:
                        mode, cmd_hex = item
                        pkt = "55aa" + mode + cmd_hex
                        all_sum = sum(int(pkt[i:i+2], 16) for i in range(0, len(pkt), 2))
                        crc = (0xFF - (all_sum & 0xFF)) & 0xFF
                        packet = bytearray.fromhex(pkt + f"{crc:02x}")
                        await self.client.write_gatt_char(CHAR_UUID, packet)
                        await asyncio.sleep(0.08)
                except asyncio.TimeoutError:
                    if self.rainbow_active: await self._rainbow_step()
            except Exception: self.client = None

    async def _rainbow_step(self):
        t = time.time() * 0.8
        r, g, b = int((math.sin(t)+1)*127), int((math.sin(t+2)+1)*127), int((math.sin(t+4)+1)*127)
        pkt = "55aa03" + f"0802{r:02x}{g:02x}{b:02x}"
        all_sum = sum(int(pkt[i:i+2], 16) for i in range(0, len(pkt), 2))
        crc = (0xFF - (all_sum & 0xFF)) & 0xFF
        try: await self.client.write_gatt_char(CHAR_UUID, bytearray.fromhex(pkt + f"{crc:02x}"))
        except: pass

    def toggle_rainbow(self):
        self.rainbow_active = not self.rainbow_active
        self.rainbow_btn.config(text="🌈 STOP RAINBOW" if self.rainbow_active else "🌈 MODO ARCOIRIS", 
                                bg="#2c3e50" if self.rainbow_active else "#1A1A1A")

    def set_intensity_only(self, brightness):
        self.rainbow_active = False
        self.rainbow_btn.config(text="🌈 MODO ARCOIRIS", bg="#1A1A1A")
        self.run_cmd(("01", "080501"), True); self.is_on = True
        self.run_cmd(("01", f"0801{brightness:02x}"), True)
        self.bright_slider.set(brightness)

    def apply_scene(self, r, g, b, brightness, white=False):
        self.rainbow_active = False
        self.rainbow_btn.config(text="🌈 MODO ARCOIRIS", bg="#1A1A1A")
        self.run_cmd(("01", "080501"), True); self.is_on = True
        if white: self.run_cmd(("01", "080903"), True)
        else: self.run_cmd(("03", f"0802{r:02x}{g:02x}{b:02x}"), True)
        self.run_cmd(("01", f"0801{brightness:02x}"), True)
        self.bright_slider.set(brightness)

    def bt_power_on(self): 
        self.update_status("⚡ ACTIVANDO BT...", "#3498DB")
        threading.Thread(target=lambda: subprocess.run(["bluetoothctl", "power", "on"])).start()
    
    def bt_power_off(self): 
        self.update_status("⚪ APAGANDO BT...", DIM_TEXT)
        threading.Thread(target=lambda: subprocess.run(["bluetoothctl", "power", "off"])).start()
    
    def audio_on(self): threading.Thread(target=lambda: subprocess.run(["bluetoothctl", "connect", AUDIO_ADDRESS])).start()
    def audio_off(self): threading.Thread(target=lambda: subprocess.run(["bluetoothctl", "disconnect", AUDIO_ADDRESS])).start()

    def on_close(self):
        self.running = False
        if self.queue: self.loop.call_soon_threadsafe(self.queue.put_nowait, None)
        self.root.after(300, self.root.destroy)

    def run_cmd(self, item, force=False):
        if not force and item[1].startswith('0801'):
            if time.time() - self.last_slider_send < 0.12: return
            self.last_slider_send = time.time()
        if self.rainbow_active:
            self.rainbow_active = False
            self.root.after(0, lambda: self.rainbow_btn.config(text="🌈 MODO ARCOIRIS", bg="#1A1A1A"))
        if self.queue: self.loop.call_soon_threadsafe(self.queue.put_nowait, item)

    def _setup_ui(self):
        f = tk.Frame(self.root, bg=BG_COLOR, pady=20); f.pack(fill="x")
        tk.Label(f, text="MY LIGHT HUB", font=("Helvetica", 22, "bold"), bg=BG_COLOR, fg=ACCENT).pack()

        # Bluetooth Sistema
        bt_f = tk.Frame(self.root, bg=BG_COLOR, padx=20); bt_f.pack(fill="x", pady=5)
        k = {"font": ("Helvetica", 8, "bold"), "relief": "flat", "pady": 5}
        tk.Button(bt_f, text="🔵 BT ON (B)", bg="#1D2A32", fg=ACCENT, **k, command=self.bt_power_on).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(bt_f, text="⚪ BT OFF (N)", bg="#1D2A32", fg=DIM_TEXT, **k, command=self.bt_power_off).pack(side="left", expand=True, fill="x", padx=2)

        scn_f = tk.LabelFrame(self.root, text=" ⚡ AJUSTES RÁPIDOS (1-4) ", bg=BG_COLOR, fg=DIM_TEXT, font=("Arial", 8), padx=10, pady=10, relief="flat", highlightbackground="#222", highlightthickness=1)
        scn_f.pack(padx=20, pady=10, fill="x")
        btns = [
            ("25%", lambda: self.set_intensity_only(64)),
            ("50%", lambda: self.set_intensity_only(128)),
            ("75%", lambda: self.set_intensity_only(191)),
            ("100%", lambda: self.set_intensity_only(255)),
            ("🎬 CINE", lambda: self.apply_scene(0, 0, 150, 20)),
            ("🔥 RELAX", lambda: self.apply_scene(255, 80, 0, 100))
        ]
        for i, (txt, cmd) in enumerate(btns):
            tk.Button(scn_f, text=txt, bg="#222", fg="white", font=("Arial", 8, "bold"), relief="flat", command=cmd).grid(row=i//2, column=i%2, sticky="nsew", padx=2, pady=2)
        scn_f.grid_columnconfigure(0, weight=1); scn_f.grid_columnconfigure(1, weight=1)

        c_f = tk.LabelFrame(self.root, text=" 🎨 LÁMPARA (Espacio = ON/OFF) ", bg=BG_COLOR, fg=DIM_TEXT, font=("Arial", 8), padx=10, pady=10, relief="flat", highlightbackground="#222", highlightthickness=1)
        c_f.pack(padx=20, pady=5, fill="x")
        tk.Button(c_f, text="ON", bg=GREEN_ACCENT, fg="white", font=("bold"), relief="flat", command=lambda: (self.run_cmd(("01", "080501"), True), setattr(self, 'is_on', True))).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(c_f, text="OFF", bg=RED_ACCENT, fg="white", font=("bold"), relief="flat", command=lambda: (self.run_cmd(("01", "080500"), True), setattr(self, 'is_on', False))).pack(side="left", expand=True, fill="x", padx=2)
        
        self.rainbow_btn = tk.Button(self.root, text="🌈 MODO ARCOIRIS", bg="#1A1A1A", fg=ACCENT, font=("Arial", 10, "bold"), relief="flat", pady=10, command=self.toggle_rainbow)
        self.rainbow_btn.pack(padx=20, pady=5, fill="x")
        tk.Button(self.root, text="☀️ MODO BLANCO", bg="#E0E0E0", fg="black", font=("Arial", 10, "bold"), relief="flat", pady=8, command=lambda: self.apply_scene(0, 0, 0, 255, True)).pack(padx=20, pady=5, fill="x")
        tk.Button(self.root, text="🎨 SELECTOR DE COLOR", bg="#3498DB", fg="white", font=("bold"), relief="flat", pady=10, command=self.choose_color).pack(padx=20, pady=5, fill="x")

        tk.Label(self.root, text="INTENSIDAD (↑ / ↓)", bg=BG_COLOR, fg=DIM_TEXT, font=("Arial", 7, "bold")).pack(pady=(10,0))
        self.bright_slider = tk.Scale(self.root, from_=1, to=255, orient="horizontal", bg=BG_COLOR, fg=TEXT_COLOR, highlightthickness=0, troughcolor="#222", activebackground=ACCENT, command=self.update_brightness)
        self.bright_slider.set(255); self.bright_slider.pack(padx=40, fill="x")

        aud_f = tk.Frame(self.root, bg=BG_COLOR, padx=20); aud_f.pack(fill="x", pady=20)
        tk.Button(aud_f, text="🔊 PARLANTE", bg="#8E44AD", fg="white", **k, command=self.audio_on).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(aud_f, text="🔇 SILENCIAR", bg="#2C3E50", fg=DIM_TEXT, **k, command=self.audio_off).pack(side="left", expand=True, fill="x", padx=2)

        self.status_label = tk.Label(self.root, text="INICIALIZANDO...", bg="#050505", fg=ACCENT, font=("Courier", 10, "bold"), pady=15)
        self.status_label.pack(side="bottom", fill="x")

    def choose_color(self):
        c = colorchooser.askcolor(title="Color")[1]
        if c: self.run_cmd(("03", f"0802{int(c[1:3],16):02x}{int(c[3:5],16):02x}{int(c[5:7],16):02x}"), True)
    def update_brightness(self, val): self.run_cmd(("01", f"0801{int(val):02x}"))

if __name__ == "__main__":
    root = tk.Tk(); app = ILinkApp(root); root.mainloop()
