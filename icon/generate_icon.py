from PIL import Image, ImageDraw, ImageFont
import os

SIZES_ICO = [16, 24, 32, 48, 64, 128, 256]
SIZES_PNG = [256]
BASE_DIR = os.path.dirname(__file__)

BG = "#1a1a2e"
ACCENT = "#0f3460"
GOLD = "#f39c12"
WHITE = "#ffffff"

OUTLINE = "#e67e22"

def create_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = max(1, size // 16)
    r = size // 2 - margin
    cx = cy = size // 2

    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=size // 5,
        fill=BG,
    )

    inner_margin = size // 6
    draw.rounded_rectangle(
        [inner_margin, inner_margin, size - inner_margin - 1, size - inner_margin - 1],
        radius=size // 8,
        fill=ACCENT,
    )

    font_size = size // 2
    try:
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    text = "\u20B9"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = (size - th) // 2 - (size // 20)

    outline_size = max(1, size // 40)
    for ox in range(-outline_size, outline_size + 1):
        for oy in range(-outline_size, outline_size + 1):
            if ox != 0 or oy != 0:
                draw.text((tx + ox, ty + oy), text, font=font, fill=OUTLINE)

    draw.text((tx, ty), text, font=font, fill=GOLD)

    return img


if __name__ == "__main__":
    ico_images = []
    for s in SIZES_ICO:
        ico_images.append(create_icon(s))

    ico_path = os.path.join(BASE_DIR, "accounting_pro.ico")
    ico_images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in SIZES_ICO],
        append_images=ico_images[1:],
    )
    print(f"Created: {ico_path} ({len(SIZES_ICO)} sizes)")

    png = create_icon(256)
    png_path = os.path.join(BASE_DIR, "accounting_pro.png")
    png.save(png_path, "PNG")
    print(f"Created: {png_path}")

    print("Done!")
