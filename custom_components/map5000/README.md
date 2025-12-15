
# Bosch MAP5000 OII – Home Assistant Custom Integration (ohne MQTT)

Diese Integration bindet die MAP5000 über die OII-REST-Schnittstelle direkt in Home Assistant ein.
Es werden **Inputs** als `binary_sensor`, **Outputs** als `switch` und ein **alarm_control_panel** (ARM/DISARM) bereitgestellt.

## Installation
1. Entpacke das ZIP und kopiere den Ordner `custom_components/map5000/` nach `config/custom_components/map5000/` deiner HA-Instanz.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → „Bosch MAP5000 OII“.
4. Basis-URL (`https://<panel-ip>`), OII-Benutzer/Passwort und TLS-Verifikation (bei self-signed Zertifikat: deaktivieren) eintragen.
5. In den **Optionen**:
   - `include_types` um `OUTPUT.` ergänzen, damit Outputs als Switches erscheinen.
   - `output_mapping` (ON/OFF) prüfen/anpassen.

## Funktionen
- Start: `GET /config` → `deviceConfiguration` (Liste) wird eingelesen.
- Initialzustände: für jedes Gerät einmal `GET /<siid>`.
- Events: `/sub` + `FETCHEVENTS` (inkl. `/inc/*`), Lease-Renewal.
- Alarm Panel: `ARM`/`DISARM` via Area-SIID, Status aus `/areas`/`/inc/*`.
- Outputs: Native `switch`-Entities, Zustand aus `on`, Schalten via `POST {"@cmd":"ON"|"OFF"}`.

## Mapping & Filter
- **Inputs** (`type_mapping`): Gerätetyp → `device_class`, `state_property`, `true/false_values`.
- **Outputs** (`output_mapping`): Gerätetyp → Plattform (`switch`), `state_property` (Standard: `on`), Befehle `turn_on`/`turn_off`.

## Hinweise
- Die Integration nutzt HTTP Digest Auth & TLS gemäß OII (self-signed Zertifikate möglich, dann `verify_tls=false`).
- Subscriptions: `bufferSize ≤ 640`, `leaseTime 10–600s`, `maxTime ≤ 100s`.

