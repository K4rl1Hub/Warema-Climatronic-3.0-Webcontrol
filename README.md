
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
2. Extract to: config/custom_components/warema_webcontrol/
3. Restart Home Assistant.
4. Add the integration via:
**Settings → Devices & Services → Add Integration → Warema WebControl**

Your folder should look like:


custom_components/
warema_webcontrol/
init.py
manifest.json
const.py
config_flow.py
webcontrol_client.py
cover.py
light.py
switch.py
sensor.py
binary_sensor.py

### HACS Installation (Custom Repository)

1. Open HACS → Integrations
2. Add custom repository:

https://github.com//warema_webcontrol
3. Category: Integration
4. Install & restart HA

---

## 🔧 Configuration

### Initial Setup
On first setup, you will be asked for:

- **Base URL** (e.g., `http://192.168.0.100`)
- **Polling interval** (recommended: `5–20 seconds`)

The integration will:
1. Query gateway language
2. Load channel blocks (`59 → 60`)
3. Run clima check (`61 → 62`)
4. Map rooms (`3 → 4`)
5. Identify device types (TYPE 3 = cover, TYPE 12 = light)
6. Create Home Assistant entities

### Changing Settings
Go to:
**Settings → Devices & Services → Warema WebControl → Options**

---

## 🏗️ Architecture & Technical Background

### Protocol Structure
Warema WebControl uses a binary protocol wrapped in hexadecimal sent over HTTP:


/protocol.xml?protocol=

Each frame:


[0] BEFEHLSCODE = 0x90
[1] Counter (0–254)
[2] Payload length
[3..] Payload bytes

### Correct Response Codes

| Function                    | Request | Response |
|-----------------------------|---------|----------|
| Language                    | 51      | 52       |
| Room info                   | 3       | 4        |
| Channel block               | 59      | 60       |
| Clima check                 | 61      | 62       |
| Sommer/Winter               | 71      | 72       |
| Automatik                   | 37      | 38       |
| Abwesend                    | 63      | 64       |
| **Channel command**         | **29**  | **30**   |
| **Polling**                 | **39**  | **40**   |
| **Busy** (retry required)   | —       | **41**   |

### Why Thread Safety Is Required
- The gateway tracks a **command counter** per session.
- Parallel requests corrupt the counter → device stops responding.
- The integration uses:
  - `threading.Lock()` (serializes all requests)
  - Shared `requests.Session()` (connection reuse)
  - Counter‑validation retry
  - RES_BUSY retry

This ensures flawless operation even with rapid commands.

---

## 🧪 Troubleshooting

### Only the first command works
Cause: command counter corrupted due to race condition.  
Fix: use the **thread‑safe client** (included in current version).

### Cover state does not update
Cause: wrong response code.  
Fix: must use `RES_POLLING = 40`.

### Light does not turn on/off
Cause: old client signature.  
Fix: update to version with compatibility wrapper.

### Integration will not load
Check:
- Folder name must be exactly:

custom_components/warema_webcontrol
- Remove any old:

custom_components/webcontrol

### Entities duplicated / ignored
Cause: old unique IDs from previous domain.  
Fix: remove old entries from  
**Settings → Devices & Services → Entities → search „webcontrol“**

---

## 🤝 Contributing

Improvements welcome!  
Ideas:

- Diagnostic panel
- Better Auslöser interpretation
- Wind/rain block sensors
- Multi‑gateway support
- Translation files

---

## 📜 License

MIT License (or your preferred one)

---

## 🙌 Acknowledgements

Thanks to the contributors validating:

- Correct RES_POLLING (40)
- Command counter behavior
- Busy retry logic
- Room/channel mapping
- Response structure of `/protocol.xml`

This integration is possible thanks to community reverse‑engineering and analysis of the Warema WebControl protocol.
