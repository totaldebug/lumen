# Migrating from the LuxPython `luxpower` integration

Lumen is a ground-up rewrite of the original
[LuxPython](https://github.com/guybw/LuxPython_DEV) integration. It uses a new
domain (`lumen` instead of `luxpower`), so **the two integrations can be
installed and run side by side** while you move over. Nothing is migrated
automatically — this guide explains what changes and how to switch cleanly.

> **TL;DR** — Install Lumen alongside `luxpower`, configure it, confirm the new
> entities report sensible values, re-point your dashboards/automations at the
> new entity IDs, then remove `luxpower`. Long-term statistics history does not
> carry across unless you take the optional step in
> [Keeping history](#keeping-statistics-history-optional).

## Why there is no in-place migration

Home Assistant ties an integration's devices, entities and their stored history
to its **domain** and each entity's **unique ID**. Lumen deliberately uses a
different domain and a different unique-ID scheme, so Home Assistant treats its
entities as brand new rather than renaming the old ones in place. That is what
lets both integrations coexist during the switch, at the cost of a manual
re-point.

## What changes

### Domain and configuration

| | `luxpower` (old) | `lumen` (new) |
| --- | --- | --- |
| Domain | `luxpower` | `lumen` |
| Configured via | UI config flow (older setups via YAML / pyscript) | UI config flow only |
| Connection | dongle pushes to Home Assistant | **client** (HA dials the dongle, default) or **server** (dongle dials HA) |
| Required details | dongle serial | dongle serial **and** inverter serial, host, port, mode |

When you add Lumen from **Settings → Devices & Services → Add Integration**,
have both the **dongle serial** and the **inverter serial** to hand. If your old
setup had the dongle connecting *out* to Home Assistant, choose **server** mode;
otherwise leave the default **client** mode.

### Devices

`luxpower` exposes a single device. Lumen models the hardware as it actually is:

- a **Dongle** device (the datalogger/communication gateway), and
- an **Inverter** device, shown nested under the dongle (`via_device`).

All telemetry and settings entities live on the **Inverter** device.

### Entity names and IDs

Names and IDs both change. Lumen uses Home Assistant's modern
device-scoped naming (`has_entity_name`), so an entity's friendly name is the
device name followed by the entity name, and there is no `Lux <id> -` prefix.

| | `luxpower` (old) | `lumen` (new, default device name "Lumen") |
| --- | --- | --- |
| Friendly name | `Lux BA1234567890 - Battery %` | `Lumen Battery` |
| Entity ID | `sensor.lux_ba1234567890_battery_percent` | `sensor.lumen_battery` |
| Unique ID | `luxpower_<dongle>_lux_battery_percent` | `<dongle>_soc` |

The exact `lumen.*` entity IDs depend on the **name you give the device** when
you add the integration (the table assumes the default, `Lumen`). After setup,
browse the Inverter device page to see the real entity IDs.

### Feature mapping

| Capability | `luxpower` | Lumen |
| --- | --- | --- |
| Live telemetry | sensors | `sensor.*` (generated from the register map) |
| Writable settings (rates, SOC limits, voltages) | numbers | `number.*` |
| On/off function flags | switches | `switch.*` |
| Charge / discharge **schedule times** | time entities | `time.*` (AC charge, charge priority, forced discharge — slot 1 enabled by default, slots 2/3 available but disabled) |
| On-grid working mode | switch (charge-first bit) | `select.*` — **On Grid Working Mode** (`Self-Consumption` / `Charge-First`) |
| Quick-charge / action buttons | buttons | not yet — use the `lumen.write_register` service for now |
| Undecoded registers | — | **new**: a diagnostic sensor and a "new register seen" event |
| Read/write an arbitrary register | — | **new**: `lumen.read_register` / `lumen.write_register` services |

## Migration procedure

1. **Install Lumen** (HACS custom repository → *Integration*) and restart Home
   Assistant. The old `luxpower` integration can stay installed.
2. **Add Lumen** from Settings → Devices & Services. Enter the host, port,
   connection mode, dongle serial and inverter serial.
   - A LuxPower dongle generally accepts **one** active connection. If you run
     both integrations in a mode that connects to the dongle at the same time,
     one may fail to read. It is simplest to point only one at the dongle at a
     time, or keep `luxpower` paused while you validate Lumen.
3. **Verify** that the new entities on the Inverter device report sensible
   values (battery %, PV power, grid frequency, etc.).
4. **Re-point your configuration** at the new entity IDs:
   - Dashboards / Lovelace cards
   - Automations, scripts and scenes
   - Energy dashboard sources (Settings → Dashboards → Energy)
   - Template sensors / helpers that reference `luxpower` entities
   - Any [pyscript](https://github.com/guybw/LuxPython_DEV/tree/main/pyscript)
     charging automations from the old project — rebuild these with Lumen's
     entities and the `lumen.write_register` service.
5. **Remove `luxpower`** once everything is working (Settings → Devices &
   Services → the LuxPower integration → Delete), and optionally uninstall it
   from HACS.

## Keeping statistics history (optional)

Long-term statistics and history are keyed by **entity ID**, so by default the
new `lumen.*` entities start with a fresh history and your old graphs stop at
the cut-over. If you want continuity for a specific energy sensor:

1. Add and verify Lumen, then **remove** `luxpower` so the old entity IDs are
   free.
2. In **Settings → Devices & Services → Entities**, open the new Lumen entity,
   and change its **Entity ID** to match the old one (e.g. rename
   `sensor.lumen_solar_array_1_total` to the previous
   `sensor.lux_..._solar_array_1_total`).

Renaming the entity ID lets the recorder continue the existing statistics
series. This is per-entity and entirely optional — most users simply accept the
break in history.

## Getting help

If a register you relied on in `luxpower` is missing from Lumen, it may simply
not be in the map yet. Check the **Undecoded registers** diagnostic sensor and
the **new register seen** event — they surface exactly the addresses Lumen has
seen but does not yet decode — and open an issue with that information.
