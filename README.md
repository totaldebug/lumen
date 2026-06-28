<a name="readme-top"></a>

[![Release][release-shield]][release-url]
[![Stargazers][stars-shield]][stars-url]
![codecov][codecov-shield]

[![Contributors][contributors-shield]][contributors-url]
[![Issues][issues-shield]][issues-url]

[![MIT License][license-shield]][license-url]
[![hacs][hacs-shield]][hacs-url]

<!-- PROJECT HEADER -->
<br />
<div align="center">
  <a href="https://github.com/totaldebug/lumen">
    <h3 align="center">Lumen</h3>
  </a>

  <p align="center">
    An efficient, modern LuxPower inverter integration for Home Assistant — with register discovery.
  </p>
    <br />
    <a href="https://github.com/totaldebug/lumen/issues/new?labels=type%2Fbug&template=bug_report.yml">Report Bug</a>
    ·
    <a href="https://github.com/totaldebug/lumen/issues/new?labels=type%2Ffeature&template=feature_request.yml">Request Feature</a>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#status">Status</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#development">Development</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

## About The Project

**Lumen — LuxPower Inverter for Home Assistant** is a ground-up rewrite of the
LuxPython integration: a layered, testable codebase with modern Home Assistant
idioms and one feature neither the original nor lxp-bridge has — it watches for
registers it doesn't understand and logs them so their meaning can be worked
out.

- **Layered & testable** — framing, the register map, and discovery live in the
  standalone, Home-Assistant-free [luxmodbus](https://github.com/totaldebug/luxmodbus)
  library; this repository is the thin Home Assistant glue (config flow,
  coordinator, entities).
- **One declarative register map** drives decoding *and* entity generation.
- **Register discovery** surfaces undecoded registers as a diagnostic sensor and
  an event, turning unknown numbers into something you can investigate.

> Replaces the `luxpower` domain with `lumen`, so both can run side by side
> during migration. Moving from the original LuxPython integration? See the
> [migration notes](docs/migration.md).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Status

Functional and loads in Home Assistant with live data. Implemented:

- Config flow (host / port / connection mode, dongle and inverter serials, with
  a reachability check)
- Transport abstraction with **client** and **server** modes (in `luxmodbus`)
- A `DataUpdateCoordinator` that polls the input and hold registers, decodes
  them, and writes settings back
- Entity platforms generated from the declarative register map: `sensor`,
  `number`, `switch`, `select` (on-grid working mode) and `time` (charge /
  discharge schedule slots)
- **Register discovery** — an *Undecoded registers* diagnostic sensor and a
  *new register seen* event, persisted across restarts
- Two-device structure: the dongle (gateway) with the inverter nested under it
- Services: `lumen.read_register` and `lumen.write_register`

Next on the roadmap: publishing `luxmodbus` to PyPI (required for HACS install),
real captured-packet test fixtures, and filling out the register long tail.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Installation

> **Note:** Lumen depends on the [luxmodbus](https://github.com/totaldebug/luxmodbus)
> library, which must be published to PyPI before the integration can be
> installed through HACS.

Once available:

1. Add this repository as a custom repository in HACS (category: *Integration*).
2. Install **Lumen — LuxPower Inverter** and restart Home Assistant.
3. Add the integration from **Settings → Devices & Services** and enter your
   dongle's host, port and connection mode.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Development

This project uses [uv](https://docs.astral.sh/uv/) and
[nox](https://nox.thea.codes/). The `luxmodbus` library is consumed from a
sibling checkout (`../luxmodbus`) during development.

```bash
git clone https://github.com/totaldebug/lumen.git
git clone https://github.com/totaldebug/luxmodbus.git
cd lumen
uv sync
uv run nox -s tests
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[release-shield]: https://img.shields.io/github/v/release/totaldebug/lumen?style=for-the-badge
[release-url]: https://github.com/totaldebug/lumen/releases
[stars-shield]: https://img.shields.io/github/stars/totaldebug/lumen.svg?style=for-the-badge
[stars-url]: https://github.com/totaldebug/lumen/stargazers
[codecov-shield]: https://img.shields.io/codecov/c/github/totaldebug/lumen?style=for-the-badge
[contributors-shield]: https://img.shields.io/github/contributors/totaldebug/lumen.svg?style=for-the-badge
[contributors-url]: https://github.com/totaldebug/lumen/graphs/contributors
[issues-shield]: https://img.shields.io/github/issues/totaldebug/lumen.svg?style=for-the-badge
[issues-url]: https://github.com/totaldebug/lumen/issues
[license-shield]: https://img.shields.io/github/license/totaldebug/lumen.svg?style=for-the-badge
[license-url]: https://github.com/totaldebug/lumen/blob/main/LICENSE
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[hacs-url]: https://github.com/hacs/integration
