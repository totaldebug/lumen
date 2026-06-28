#!/usr/bin/env python3
"""Rasterize Lumen logo SVGs to PNGs at the sizes a HACS/HA integration needs.
Usage: python build_assets.py
Requires: pip install cairosvg
"""

import cairosvg, os

OUT = "assets"
os.makedirs(OUT, exist_ok=True)

# icon sizes (square) — HA brands repo uses icon.png (256) and icon@2x.png (512)
for size in (48, 64, 128, 256, 512):
    cairosvg.svg2png(
        url="lumen-icon-dark.svg", write_to=f"{OUT}/icon-{size}.png", output_width=size, output_height=size
    )

# HA brands convention names
cairosvg.svg2png(url="lumen-icon-dark.svg", write_to=f"{OUT}/icon.png", output_width=256, output_height=256)
cairosvg.svg2png(url="lumen-icon-dark.svg", write_to=f"{OUT}/icon@2x.png", output_width=512, output_height=512)

# wordmarks (HA brands: logo.png up to 512 tall is fine)
cairosvg.svg2png(url="lumen-wordmark-dark.svg", write_to=f"{OUT}/logo.png", output_width=900, output_height=260)
cairosvg.svg2png(url="lumen-wordmark-dark.svg", write_to=f"{OUT}/logo@2x.png", output_width=1800, output_height=520)
cairosvg.svg2png(url="lumen-wordmark-light.svg", write_to=f"{OUT}/logo-light.png", output_width=900, output_height=260)

print("Wrote assets to", OUT)
