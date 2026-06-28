# Lumen — Logo Assets

The Lumen mark is an **aperture**: a cyan ring with a glowing amber core. It reads
as a camera/lens aperture (light being measured), a sun, and an inverter status
indicator — and ties to the project's discovery theme (shining light on the unknown).

## Colours
- Panel / background: `#0e1419`
- Ring (cyan): `#4fd1c5` (gradient `#5fe0d2 → #2bb3a6`)
- Core / signature accent (photon amber): `#ffb627` (gradient `#ffd06b → #e8920c`)
- Text (dark bg): `#e8eef2` · subtitle `#9fb0bd`

## Files
| File | Use |
|---|---|
| `lumen-icon-dark.svg` | Square app/integration icon (vector, source of truth) |
| `lumen-wordmark-dark.svg` | Horizontal logo + subtitle, dark backgrounds |
| `lumen-wordmark-light.svg` | Same, for light backgrounds / light-mode READMEs |
| `assets/icon.png`, `icon@2x.png` | 256 / 512px — Home Assistant brands convention |
| `assets/icon-{48,64,128,256,512}.png` | Favicon / various raster sizes |
| `assets/logo.png`, `logo@2x.png` | Wordmark raster (dark) |
| `assets/logo-light.png` | Wordmark raster (light) |
| `build_assets.py` | Regenerate all PNGs from the SVGs (`pip install cairosvg`) |

## Font note
The wordmark SVGs reference a geometric sans via a system font stack so they stay
editable. For pixel-identical rendering everywhere (GitHub, HACS), either:
- convert the `<text>` to outlined paths in a vector editor, or
- swap in a webfont (e.g. Inter / Montserrat 800) and embed it.

## Home Assistant brands
To get the icon to show in HA's integration list, the PNGs eventually go in the
`home-assistant/brands` repo under `custom_integrations/lumen/` as `icon.png` and
`logo.png` (and `@2x` variants). That's a separate PR from the integration itself.
