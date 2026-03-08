"""Generate static OG images for site pages (main, about, api, error).

Uses the same Pillow rendering style as the vinyl OG generator:
same fonts, colors, and dark background.

Usage:
    python -m vinylscrape.og.generate_static [output_dir]

If output_dir is not specified, defaults to ../frontend/public/og/
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Reuse constants from the main generator
_FONTS_DIR = Path(__file__).parent / "fonts"

# Canvas dimensions (standard OG)
WIDTH = 1200
HEIGHT = 630

# Colours (same palette as vinyl OG images)
BG_COLOR = (23, 23, 23)  # #171717
AMBER_COLOR = (217, 119, 6)  # #d97706
WHITE_COLOR = (255, 255, 255)
BRAND_COLOR = (115, 115, 115)  # neutral-500
SUBTITLE_COLOR = (163, 163, 163)  # neutral-400


def _load_font(bold: bool = False, size: int = 36) -> ImageFont.FreeTypeFont:
    filename = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    path = _FONTS_DIR / filename
    return ImageFont.truetype(str(path), size=size)


def _wrap_text(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_page_og(
    title: str,
    subtitle: str,
    output_path: Path,
) -> None:
    """Generate a static OG image for a site page.

    Layout: centered text with VinylScrape branding.
    - "VinylScrape" in bold at top (with amber accent)
    - Page title in white, bold
    - Subtitle in neutral gray
    - Branding line at bottom
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Fonts
    brand_large_font = _load_font(bold=True, size=56)
    title_font = _load_font(bold=True, size=48)
    subtitle_font = _load_font(bold=False, size=28)
    tagline_font = _load_font(bold=False, size=22)

    max_text_width = WIDTH - 160  # 80px padding each side
    center_x = WIDTH // 2

    # --- Draw decorative amber accent bar at top ---
    bar_width = 80
    bar_height = 5
    draw.rectangle(
        [center_x - bar_width // 2, 120, center_x + bar_width // 2, 120 + bar_height],
        fill=AMBER_COLOR,
    )

    # --- "VinylScrape" brand name (draw each part separately to avoid overlay artifacts) ---
    vinyl_text = "Vinyl"
    scrape_text = "Scrape"
    vinyl_bbox = draw.textbbox((0, 0), vinyl_text, font=brand_large_font)
    vinyl_w = vinyl_bbox[2] - vinyl_bbox[0]
    full_text = vinyl_text + scrape_text
    full_bbox = draw.textbbox((0, 0), full_text, font=brand_large_font)
    full_w = full_bbox[2] - full_bbox[0]
    brand_y = 148
    brand_start_x = center_x - full_w // 2
    draw.text((brand_start_x, brand_y), vinyl_text, font=brand_large_font, fill=WHITE_COLOR)
    draw.text(
        (brand_start_x + vinyl_w, brand_y), scrape_text, font=brand_large_font, fill=AMBER_COLOR
    )

    # --- Page title ---
    title_y = 240
    title_lines = _wrap_text(draw, title, title_font, max_text_width)
    for line in title_lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_w = bbox[2] - bbox[0]
        draw.text((center_x - line_w // 2, title_y), line, font=title_font, fill=WHITE_COLOR)
        title_y += (bbox[3] - bbox[1]) + 12

    # --- Subtitle ---
    subtitle_y = title_y + 16
    sub_lines = _wrap_text(draw, subtitle, subtitle_font, max_text_width)
    for line in sub_lines[:2]:
        bbox = draw.textbbox((0, 0), line, font=subtitle_font)
        line_w = bbox[2] - bbox[0]
        draw.text(
            (center_x - line_w // 2, subtitle_y), line, font=subtitle_font, fill=SUBTITLE_COLOR
        )
        subtitle_y += (bbox[3] - bbox[1]) + 8

    # --- Bottom decorative bar ---
    draw.rectangle(
        [
            center_x - bar_width // 2,
            HEIGHT - 110,
            center_x + bar_width // 2,
            HEIGHT - 110 + bar_height,
        ],
        fill=AMBER_COLOR,
    )

    # --- Tagline at bottom ---
    tagline = "vinylscrape.cfb.wtf"
    tag_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tag_w = tag_bbox[2] - tag_bbox[0]
    draw.text(
        (center_x - tag_w // 2, HEIGHT - 80),
        tagline,
        font=tagline_font,
        fill=BRAND_COLOR,
    )

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG", optimize=True)
    print(f"  Generated: {output_path} ({output_path.stat().st_size} bytes)")


# Page definitions
PAGES = [
    {
        "filename": "main.png",
        "title": "Search Vinyl Records from Georgian Shops",
        "subtitle": "Compare prices, check availability, and find the best deals on vinyl records in Georgia.",
    },
    {
        "filename": "about.png",
        "title": "About VinylScrape",
        "subtitle": "A unified search and price-comparison tool for vinyl records sold in Georgian shops.",
    },
    {
        "filename": "api.png",
        "title": "API Reference",
        "subtitle": "REST API documentation for the VinylScrape vinyl record aggregator.",
    },
    {
        "filename": "error.png",
        "title": "Page Not Found",
        "subtitle": "The page you are looking for does not exist or has been moved.",
    },
]


def main() -> None:
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    else:
        output_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "og"

    print(f"Generating static OG images in: {output_dir}")
    for page in PAGES:
        generate_page_og(
            title=page["title"],
            subtitle=page["subtitle"],
            output_path=output_dir / page["filename"],
        )
    print("Done!")


if __name__ == "__main__":
    main()
