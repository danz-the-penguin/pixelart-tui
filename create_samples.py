"""Generate sample input sprite and showcase retro conversions."""

from PIL import Image, ImageDraw
import math
import os


def generate_sample_sprite(output_path="sample_input.png"):
    """Draw a vibrant 256x256 fantasy potion flask sprite with transparent background."""
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cork stopper
    draw.rectangle([110, 30, 146, 55], fill=(160, 95, 45, 255))
    draw.rectangle([106, 50, 150, 60], fill=(130, 70, 30, 255))

    # Glass neck
    draw.rectangle([112, 60, 144, 100], fill=(200, 230, 255, 200))
    draw.rectangle([108, 95, 148, 105], fill=(160, 200, 240, 230))

    # Glass flask body (round bulb)
    center = (128, 160)
    radius = 70
    draw.ellipse([center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius], fill=(180, 220, 255, 120))

    # Liquid inside (vibrant glowing magic elixir)
    liquid_radius = 62
    liquid_center = (128, 168)
    draw.ellipse([liquid_center[0] - liquid_radius, liquid_center[1] - liquid_radius, liquid_center[0] + liquid_radius, liquid_center[1] + liquid_radius], fill=(240, 20, 100, 230))

    # Liquid top meniscus
    draw.ellipse([128 - 45, 125, 128 + 45, 145], fill=(255, 120, 180, 255))

    # Glowing bubbles
    bubbles = [(110, 180, 8), (145, 190, 6), (120, 205, 10), (135, 160, 7), (105, 150, 5)]
    for bx, by, br in bubbles:
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill=(255, 240, 250, 255))

    # Glass reflection highlight (curved shine on left)
    for a in range(120, 210, 5):
        rad = math.radians(a)
        hx = int(center[0] + (radius - 12) * math.cos(rad))
        hy = int(center[1] + (radius - 12) * math.sin(rad))
        draw.ellipse([hx - 4, hy - 4, hx + 4, hy + 4], fill=(255, 255, 255, 230))

    img.save(output_path)
    print(f"Generated sample sprite: {output_path} ({size[0]}x{size[1]})")
    return output_path


if __name__ == "__main__":
    generate_sample_sprite()
