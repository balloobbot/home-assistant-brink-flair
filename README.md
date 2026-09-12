# Brink Flair for Home Assistant

A Home Assistant integration for **Brink heat recovery appliances** — the Flair
range and its siblings, anything built on the UWA2-B control PCB, with or
without the Plus extension PCB UWA2-E.

It reads what the appliance measures, exposes its settings, and can drive the
ventilation: set a switch position or a flow rate, put the appliance into
standby, open the bypass, reset the filter warning.

The appliance is a Modbus RTU device on RS-485. Reach it with a USB RS-485
adapter on the machine running Home Assistant, or over the network through a
serial server or a Modbus gateway — see
[Which box do I have?](#which-box-do-i-have).

## What you get

| Platform | Entities |
| --- | --- |
| Fan | The ventilation: on/off through standby, and the four switch positions as presets |
| Sensor | Flows, fan and anemometer speeds, temperatures, humidities, pressures, CO2, the lifetime counters, and every status register as a named state |
| Binary sensor | The filter warning, and the UWA2-E's contacts and relay outputs |
| Number | The Modbus flow-rate setpoint |
| Select | Bypass mode, flow type, signal-output mode |
| Button | Reset filter warning, restart appliance |

Hardware the appliance does not have gets no entities. The display, the
UWA2-E, a geo heat exchanger and up to four CO2 sensors are each probed once
during setup, so you configure nothing to match your unit.

Each sub-system is read on its own, so one that stops answering takes only its
own entities unavailable. The lifetime counters stay available whatever the
appliance does and restore across a restart, so the energy and long-term
statistics keep their history.

## Before you start

1. Connect the Modbus line to **X15 on the UWA2-B**, or to **X06 on the
   UWA2-E** if the appliance is a Plus version. Cascaded appliances are
   reached through the master's UWA2-E.
2. The RS-485 terminator is the jumper **X12** on the UWA2-B (**X07** on the
   UWA2-E). Remove it unless the appliance sits at the end of the bus. On a
   Plus appliance, X12, X121 and X122 must be fitted on the UWA2-B.
3. On the appliance's display, set **step 14.1 to `Modbus`**. Without it the
   port does nothing.
4. Note steps **14.2** (slave address, factory 20), **14.3** (baud rate,
   factory 19k2) and **14.4** (parity, factory Even). You need all three.

Always pull the power plug before working inside the appliance.

## Install

### Through HACS

1. In Home Assistant, open **HACS**.
2. Open the three-dot menu at the top right and choose **Custom
   repositories**.
3. Paste `https://github.com/balloobbot/home-assistant-brink-flair`, choose
   the **Integration** category, and select **Add**.
4. Search HACS for **Brink Flair** and select **Download**.
5. Restart Home Assistant.

### By hand

Copy `custom_components/brink_flair` into your Home Assistant `config`
directory, so you end up with `config/custom_components/brink_flair`, and
restart Home Assistant.

### Requirements

Home Assistant **2026.9.0 or newer**. The integration asks Home Assistant's
own `modbus` integration for its connection, which is what lets several
integrations share one RS-485 line or one gateway without competing for it.
`async_get_unit`, the API that does so, landed in 2026.9.0.

Nothing is installed from PyPI: the device library is bundled — see
[The bundled library](#the-bundled-library).

## Set it up

1. Go to **Settings → Devices & services → Add integration**, and search for
   **Brink Flair**.
2. Choose how the appliance is reached:
   - **A serial adapter on this machine** — give the device path (for
     example `/dev/ttyUSB0`), the unit id, and the baud rate, parity and stop
     bits from steps 14.2 to 14.4.
   - **A serial server on the network** — give its host, port, unit id, and
     the baud rate the box runs its RS-485 line at. Parity and stop bits are
     set on the box; the baud rate is asked for because it spaces the frames.
   - **A Modbus gateway on the network** — give its host and port, and the
     unit id.
3. Home Assistant reads the appliance's identity to check the settings, then
   creates the device.

### Which box do I have?

The two network options are different products, and they do not speak the
same protocol:

| | What it does | What crosses the network |
| --- | --- | --- |
| **Serial server** | Forwards the RS-485 line byte for byte | Modbus RTU frames, CRC and all |
| **Modbus gateway** | Terminates Modbus TCP and re-frames to RTU | Modbus TCP, with an MBAP header and no CRC |

USR-TCP232 and Waveshare RS485-TO-ETH boxes are usually run as serial
servers; a Moxa MGate is a gateway. **Many boxes are either, depending on how
they are configured**, and nothing on the network says which — so if one
choice times out against a box you believe is wired and addressed correctly,
try the other before suspecting the appliance.

A serial server is stored as a serial link over a `socket://` device, because
that is what it is. Home Assistant keys connections on that, so this
integration shares one socket with anything else reaching the same box rather
than opening a second one onto a half-duplex line. A gateway is stored as a
Modbus TCP connection and shares in the same way.

To add a second appliance, repeat the flow with its own unit id. Appliances on
one line or one gateway share a connection automatically.

If setup fails with "the appliance did not answer", work through step 14.1,
the unit id, the A/B wiring polarity and the terminator in that order, then
try the other network option. The parity is the setting people miss most: the
factory default is **Even**, not the Modbus-usual None.

## Driving the ventilation

Setting the fan's preset, or the flow-rate number, puts the appliance under
Modbus control — the spec's register 8000 — and it stays there until something
releases it. The fan reports the mode the appliance is actually in, so a
position set on the appliance's own display shows up here too.

The appliance's **`auto` mode has no preset**. Register 8001 has no code for
it, so it can be reported but not asked for; while the appliance is on auto
the fan shows no preset.

Turning the fan off puts the appliance into standby, which is a separate
register and works whether or not Modbus is driving the flow.

**A power cycle forgets all of it.** The spec is explicit: after the appliance
loses mains, registers 8000-8011 are back to their defaults and the desired
flows must be set again. An automation that drives the appliance should set
the mode it wants rather than assume the appliance kept it.

### The flow-rate slider's maximum

The number entity runs to 500 m³/h in steps of 5. The spec makes the real
minimum and maximum depend on the appliance model and gives no register to
read them from, so that bound is this integration's rather than your
appliance's. Values above what your unit can do are for the appliance to
refuse.

## How often it polls

The readings are polled every **30 seconds** and the settings every **15
minutes**. A readings poll is 19 Modbus requests and a settings poll 17 —
which sounds like a lot and is under a second at 19200 baud. The library's
README explains why it reads that many and how to make it read fewer.

## Diagnostics

**Settings → Devices & services → Brink Flair → the device → Download
diagnostics** gives you every register the integration reads with its raw
value, which optional modules were found, and what the last two polls managed.
Attach it to an issue. The serial number is left out.

The dump loads straight back into the library's mock backend, so a report can
become a regression test with no hardware involved.

## The bundled library

The Modbus work lives in
[brink-flair-modbus](https://github.com/balloobbot/brink-flair-modbus), a
standalone library built on
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection).
It has no Home Assistant dependency and is tested against an in-memory mock,
so the register map is verified without hardware and without Home Assistant.

A copy of it is **vendored** into `custom_components/brink_flair/`, so
installing this integration installs the library with it — there is nothing to
fetch from PyPI and no version to keep in step. `modbus-connection` itself
comes from Home Assistant's `modbus` integration, which already requires it.

To refresh the copy after changing the library:

```bash
./script/vendor.sh ../brink-flair-modbus
```

CI fails if the vendored copy has drifted from the library's `main`, and if
the translation files no longer match the library's enums.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

The tests run the integration against Home Assistant with the library's own
mock appliance behind it, so a config flow, a poll, a write and a diagnostics
download are all exercised with no device. After changing an entity, regenerate
the translation files:

```bash
uv run --with modbus-connection script/generate_strings.py
```

## Not affiliated with Brink

This is a community integration. Brink Climate Systems has nothing to do with
it, does not support it, and it may stop working if Brink changes the register
map. The register definitions come from Brink's published *Installation
regulations Modbus UWA2-B/UWA2-E* (614882-D), which is committed in the
library's repository.

## License

MIT
