#!/usr/bin/env python3
"""OğuzDows görsellerini Pillow ile çevrimdışı üretir; uzak tema indirmez."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

INK = "#131620"
PAPER = "#fff9ef"
RED = "#c93246"
TURQUOISE = "#3fc5c1"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        "/usr/share/fonts/truetype/inter/Inter-SemiBold.otf" if bold else "/usr/share/fonts/truetype/inter/Inter-Regular.otf",
        "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf" if bold else "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    raise RuntimeError("Türkçe karakterleri destekleyen bir sistem yazı tipi bulunamadı.")


def save(image: Image.Image, root: Path, target: str) -> None:
    path = root / target.lstrip("/")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def star(cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    return [
        (cx + math.cos(i * math.pi / 5) * radius * (0.4 if i % 2 else 1),
         cy + math.sin(i * math.pi / 5) * radius * (0.4 if i % 2 else 1))
        for i in range(10)
    ]


def emblem(size: int, tile: bool = False) -> Image.Image:
    # 3x örnekleme; küçük panel ikonlarında da temiz kenarlar.
    scale = size * 3
    image = Image.new("RGBA", (scale, scale))
    draw = ImageDraw.Draw(image)
    if tile:
        draw.rounded_rectangle((0, 0, scale - 1, scale - 1), radius=scale / 4, fill=RED)
    mask = Image.new("L", image.size)
    md = ImageDraw.Draw(mask)
    md.ellipse((scale * .15, scale * .23, scale * .69, scale * .77), fill=255)
    md.ellipse((scale * .30, scale * .28, scale * .74, scale * .72), fill=0)
    image.alpha_composite(Image.composite(Image.new("RGBA", image.size, PAPER), Image.new("RGBA", image.size), mask))
    draw = ImageDraw.Draw(image)
    draw.polygon(star(scale * .73, scale * .50, scale * .135), fill=PAPER)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def text_image(text: str, size: int, color: str, bold: bool = False) -> Image.Image:
    face = font(size, bold)
    box = face.getbbox(text)
    image = Image.new("RGBA", (box[2] - box[0] + 4, box[3] - box[1] + 8))
    ImageDraw.Draw(image).text((2 - box[0], 4 - box[1]), text, font=face, fill=color)
    return image


def kilim(draw: ImageDraw.ImageDraw, width: int, y: int, unit: int, color: str) -> None:
    for x in range(-unit, width + unit, unit * 2):
        draw.line([(x, y), (x + unit, y - unit), (x + unit * 2, y), (x + unit, y + unit), (x, y)], fill=color, width=2)
        r = max(2, unit // 4)
        draw.polygon([(x + unit - r, y), (x + unit, y - r), (x + unit + r, y), (x + unit, y + r)], fill=TURQUOISE)


def wallpaper() -> Image.Image:
    width, height = 1920, 1080
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / height
        draw.line((0, y, width, y), fill=(int(25 - t * 11), int(29 - t * 12), int(41 - t * 16)))
    art = Image.new("RGBA", image.size)
    ad = ImageDraw.Draw(art)
    ad.polygon([(1120, 0), (1920, 0), (1920, 850)], fill=(138, 28, 48, 34))
    ad.polygon([(1510, 0), (1920, 0), (1920, 430)], fill=(201, 50, 70, 18))
    for r in range(480, 1000, 95):
        ad.ellipse((1510 - r, 480 - r, 1510 + r, 480 + r), outline=(217, 205, 192, 10), width=2)
    image = Image.alpha_composite(image.convert("RGBA"), art)
    mark = emblem(560)
    image.alpha_composite(mark, (1190, 215))
    draw = ImageDraw.Draw(image)
    draw.line((150, 405, 150, 604), fill=RED, width=4)
    draw.text((183, 405), "AY YILDIZ / 01", font=font(16, True), fill=TURQUOISE)
    draw.text((176, 433), "OğuzDows", font=font(102, True), fill=PAPER)
    draw.text((183, 575), "Köklerinden güç alır.", font=font(26), fill="#b9becb")
    draw.text((183, 614), "Özgürce üretir.", font=font(26), fill="#b9becb")
    draw.text((152, 966), "TÜRKÇE  /  YALIN  /  ÖZGÜR", font=font(13, True), fill="#8d98a9")
    kilim(draw, width, 1048, 16, "#672c3b")
    return image.convert("RGB")


def boot_background(width: int, height: int) -> Image.Image:
    # BIOS menü metnini SYSLINUX çizer; başlık/fontlar resme gömülür.
    image = Image.new("RGBA", (640, 480), INK)
    draw = ImageDraw.Draw(image)
    draw.polygon([(480, 0), (640, 0), (640, 160)], fill="#241b29")
    image.alpha_composite(emblem(84), (278, 26))
    title = text_image("OğuzDows", 42, PAPER, True)
    image.alpha_composite(title, ((640 - title.width) // 2, 117))
    subtitle = text_image("KÖKLERİNDEN GÜÇ ALIR.", 11, TURQUOISE, True)
    image.alpha_composite(subtitle, ((640 - subtitle.width) // 2, 171))
    draw = ImageDraw.Draw(image)
    draw.line((280, 200, 360, 200), fill=RED, width=2)
    kilim(draw, 640, 462, 12, "#672c3b")
    return image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)


def window_theme(root: Path) -> None:
    base = "usr/share/themes/OguzDows/xfwm4/"
    for state in ("active", "inactive"):
        bg = "#1c202a" if state == "active" else "#191c24"
        edge = RED if state == "active" else "#363b49"
        for part in ("title-1", "title-2", "title-3", "title-4", "title-5", "top-left", "top-right"):
            image = Image.new("RGBA", (5, 32), bg)
            ImageDraw.Draw(image).line((0, 0, 5, 0), fill=edge)
            save(image, root, base + f"{part}-{state}.png")
        for part, size in (("left", (3, 1)), ("right", (3, 1)), ("bottom", (1, 3)), ("bottom-left", (3, 3)), ("bottom-right", (3, 3))):
            save(Image.new("RGBA", size, bg), root, base + f"{part}-{state}.png")
    for state in ("active", "inactive", "prelight", "pressed"):
        color = "#78808f" if state == "inactive" else PAPER
        for button in ("close", "hide", "maximize", "maximize-toggled", "menu"):
            image = Image.new("RGBA", (28 * 3, 32 * 3))
            draw = ImageDraw.Draw(image)
            if state in ("prelight", "pressed"):
                draw.rounded_rectangle((6, 12, 78, 84), radius=15, fill=RED if button == "close" else "#37424b")
            if button == "close":
                draw.line((30, 36, 54, 60), fill=color, width=4)
                draw.line((54, 36, 30, 60), fill=color, width=4)
            elif button == "hide":
                draw.line((27, 57, 57, 57), fill=color, width=4)
            elif button.startswith("maximize"):
                draw.rectangle((28, 34, 56, 62), outline=color, width=3)
                if button.endswith("toggled"):
                    draw.line((34, 28, 62, 28, 62, 56), fill=color, width=3)
            else:
                for y in (36, 48, 60):
                    draw.line((27, y, 57, y), fill=TURQUOISE if state != "inactive" else color, width=3)
            save(image.resize((28, 32), Image.Resampling.LANCZOS), root, base + f"{button}-{state}.png")
    path = root / base / "themerc"
    path.write_text("""active_text_color=#fff9ef
inactive_text_color=#939baa
active_text_shadow_color=#1c202a
inactive_text_shadow_color=#191c24
button_offset=3
button_spacing=1
full_width_title=true
title_horizontal_offset=8
title_vertical_offset=0
shadow_delta_height=2
shadow_delta_width=2
shadow_delta_x=0
shadow_delta_y=2
""")


def render(root: Path) -> None:
    save(wallpaper(), root, "usr/share/backgrounds/oguzdows/wallpaper.png")
    for size in (24, 32, 48, 64, 128, 256):
        save(emblem(size, tile=True), root, f"usr/share/icons/hicolor/{size}x{size}/apps/oguzdows.png")
    brand = "usr/share/oguzdows/brand/"
    save(emblem(128, tile=True), root, brand + "oguzdows.png")
    for name, size in (("boot-bios", (640, 480)), ("boot-efi", (800, 600))):
        save(boot_background(*size), root, brand + name + ".png")
    plymouth = "usr/share/plymouth/themes/oguzdows/"
    for name, image in {
        "emblem": emblem(128),
        "wordmark": text_image("OğuzDows", 48, PAPER, True),
        "tagline": text_image("Köklerinden güç alır.", 15, "#aeb9c8"),
        "track": Image.new("RGBA", (280, 4), "#343948"),
        "fill": Image.new("RGBA", (280, 4), RED),
        "dot": Image.new("RGBA", (4, 4), TURQUOISE),
    }.items():
        save(image, root, plymouth + name + ".png")
    installer = "usr/share/calamares/branding/oguzdows/"
    save(emblem(160, tile=True), root, installer + "logo.png")
    save(boot_background(640, 480).crop((80, 20, 560, 210)), root, installer + "welcome.png")
    window_theme(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Üretilen dosyaların kök dizini")
    args = parser.parse_args()
    render(args.root.resolve())


if __name__ == "__main__":
    main()
