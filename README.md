# iLink Lamp Control Hub 💡🛰️

A professional Python-based desktop controller for iLink Bluetooth Low Energy (BLE) smart lamps. This project features real-time control, reverse-engineered protocols, and high-performance background connection management for Linux environments.

---

## 🚀 Overview

This application provides a premium, dark-themed control interface for iLink smart lamps, bypassing the need for poorly optimized mobile apps. It focuses on **instant response**, **keyboard-centric workflow**, and **system-level integration**.

### Key Features
- **Instant Response**: Maintains a persistent background BLE connection.
- **Smart Queueing**: Implements command compaction to prevent Bluetooth lag/overflow.
- **Scene Presets**: Quick access to specialized lighting ("CINE", "RELAX").
- **Manual Control**: Full RGB color picker and brightness slider.
- **System Integration**: Hotkeys for system Bluetooth power and Audio Speaker connection.
- **Rainbow Mode**: Smooth, mathematical color cycling.
- **Keyboard Hotkeys**:
  - `Space`: Toggle Power (ON/OFF).
  - `1, 2, 3, 4`: Intensity Presets (25%, 50%, 75%, 100%).
  - `Up / Down Arrows`: Fine-tuned brightness adjustment.
  - `B / N`: System Bluetooth Power ON / OFF.

---

## 🛠️ Technical Stack & Architecture

### Core Technologies
- **Python 3.10+**: Core logic.
- **Tkinter**: GUI framework (Dark Mode with Neon accents).
- **Bleak**: Asynchronous BLE communication library.
- **Asyncio + Threading**: Multi-threaded architecture to keep the UI responsive during BLE operations.
- **BlueZ (via bluetoothctl)**: Native Linux Bluetooth stack management.

### Architecture Highlights
1. **Background Engine**: A dedicated thread runs the `asyncio` event loop.
2. **Command Compactor**: The app evaluates the command queue in real-time. If multiple brightness commands are queued, it discards outdated ones and only sends the latest bit of data, ensuring zero-latency feel during slider movement.
3. **Checksum Engine**: Implements a custom CRC calculation (Parity Check) discovered during reverse engineering.

---

## 🔍 Reverse Engineering Findings

The lamp uses a proprietary binary protocol over a single GATT characteristic.
- **MAC (BLE)**: `A8:D2:CD:C7:9C:AC`
- **GATT UUID**: `0000a040-0000-1000-8000-00805f9b34fb`
- **Protocol Header**: `55 AA`
- **Main Command Types**:
  - `0x01`: System/White Lighting.
  - `0x03`: RGB Color Lighting.

*For full protocol documentation, see [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md).*

---

## 📦 Installation & Usage

### Prerequisites (Linux)
```bash
sudo apt update
sudo apt install python3-tk bluetooth bluez
pip install bleak
```

### Running the App
```bash
python3 ilink_app.py
```
*Note: Ensure your user has permissions for Bluetooth (usually part of 'lp' or 'bluetooth' group).*

---

## 📂 Project Structure
- `ilink_app.py`: Main application code (UI + Engine).
- `REVERSE_ENGINEERING.md`: Detailed breakdown of the protocol and hardware quirks.
- `README.md`: This documentation.

---

## 🤖 Information for AI Agents / Future Developers
- **Concurrency**: Do not run BLE operations in the main thread (it will freeze Tkinter).
- **Latency**: The chip (Jieli) has a small buffer. Pauses of ~0.08s between burst commands (like scenes) are necessary for stability.
- **System Scope**: Bluetooth system commands rely on `subprocess` calling `bluetoothctl`. If porting to Windows, these specific functions need a PowerShell/WinAPI replacement.

---

## 📜 Credits & License
Developed as a custom solution for high-performance IoT control using reverse engineering techniques.
