
# Warema WebControl – Home Assistant Integration
*A fully local integration for Warema WebControl blinds, shutters, lights, and automation systems.*

---

## 🧭 Overview

The **Warema WebControl** custom integration enables **local LAN control** of WAREMA shading systems through the official WebControl gateway.  
It adds full Home Assistant support for covers, lights, sensors, switches, and automatic polling of device states.

This integration:

- Works **fully locally** (no cloud required)
- Controls **blinds, shutters, and rafstores** (TYPE 3)
- Controls **lights** (TYPE 12)
- Supports **open / close / stop / set position**
- Provides **real‑time polling** via the gateway protocol
- Implements a **Config Flow** (no YAML needed)
- Offers adjustable **polling interval**
- Handles **Auslöser (cause codes)** for movement blocks
- Includes switches for **Abwesend** and **Automatik**
- Includes sensors for **language** and **Sommer/Winter**
- Implements a **thread‑safe, session‑based protocol engine** (critical for correct operation)
- Correctly handles protocol features (busy‑retry, counter validation, polling response = 40)

---

## ✨ Features

### Covers (Blinds / Shutters / Raffstores)
- Open, Close, Stop
- Set absolute position (0–100)
- Automatically maps WebControl’s **0–200** to **0–100**
- Reads last Auslöser (cause code)
- Fully stateful via periodic polling

### Lights
- ON/OFF control
- Correct HA color mode: `ColorMode.ONOFF`
- State determined via polling (`lastp`)

### Polling System
- Uses a Home Assistant **DataUpdateCoordinator**
- Poll packet: `TEL_POLLING = 39`
- **Correct response**: `RES_POLLING = 40`
- Thread‑safe request pipeline
- Automatic retries for `RES_BUSY = 41`
- Automatic command‑counter validation

### Switches
- `switch.abwesend`
- `switch.automatik`

### Sensors
- `sensor.webcontrol_language`
- `binary_sensor.sommer_winter_aktiv`

### Configuration / Options
- Local gateway URL
- Polling interval (seconds)
- Automatic mapping of rooms → channels → device types

---

## 📦 Installation

### Manual installation

1. Download the latest release ZIP.
2. Extract to:
