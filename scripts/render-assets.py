#!/usr/bin/env python3
"""OğuzDows görsellerini Pillow ile çevrimdışı üretir; uzak tema indirmez."""
from __future__ import annotations

import argparse
import json
import math
import shutil
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


def landscape_sky(top: str, bottom: str) -> Image.Image:
    image = Image.new("RGB", (1920, 1080))
    draw = ImageDraw.Draw(image)
    a, b = (tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)) for color in (top, bottom))
    for y in range(1080):
        t = y / 1079
        draw.line((0, y, 1920, y), fill=tuple(round(x * (1 - t) + z * t) for x, z in zip(a, b)))
    return image


def sign_landscape(image: Image.Image, name: str) -> Image.Image:
    draw = ImageDraw.Draw(image)
    draw.line((1460, 942, 1510, 942), fill=TURQUOISE, width=3)
    draw.text((1460, 960), name, font=font(23, True), fill=PAPER)
    draw.text((1460, 998), "OğuzDows / Türkiye koleksiyonu", font=font(13), fill="#d2d9dd")
    return image


def istanbul() -> Image.Image:
    image = landscape_sky("#192438", "#d49b83")
    d = ImageDraw.Draw(image)
    d.ellipse((1380, 140, 1620, 380), fill="#e6b791")
    d.polygon([(0, 595), (210, 570), (400, 598), (760, 555), (1000, 580), (1340, 550), (1660, 500), (1920, 530), (1920, 1080), (0, 1080)], fill="#496476")
    # Tarihî yarımada silueti ve minareler; ufukta sakin bir çizgi.
    for x, h in ((1460, 74), (1515, 110), (1645, 104), (1700, 64)):
        d.rectangle((x, 545 - h, x + 7, 560), fill="#303c50")
        d.polygon([(x - 3, 545 - h), (x + 3, 526 - h), (x + 10, 545 - h)], fill="#303c50")
    d.rectangle((1530, 505, 1635, 565), fill="#303c50")
    d.ellipse((1530, 453, 1635, 555), fill="#303c50")
    # Boğaz köprüsü.
    for x in (825, 1275):
        d.rectangle((x, 370, x + 14, 635), fill="#29384b")
        d.rectangle((x - 6, 395, x + 20, 407), fill="#29384b")
    points = [(x, int(388 + 113 * (1 - ((x - 1057) / 225) ** 2))) for x in range(832, 1283, 5)]
    d.line([(590, 560), (832, 388), *points, (1525, 560)], fill="#e6bf9a", width=3)
    for x in range(850, 1275, 23):
        y = int(388 + 113 * (1 - ((x - 1057) / 225) ** 2))
        d.line((x, y, x, 569), fill="#a2a4a7", width=1)
    d.line((580, 574, 1540, 574), fill="#29384b", width=10)
    for y in range(690, 1050, 26):
        x = 300 + (y * 29) % 670
        d.line((x, y, x + 230, y), fill="#65818a", width=2)
    # Kız Kulesi, öndeki küçük adacık.
    d.ellipse((1190, 811, 1440, 851), fill="#263747")
    d.rectangle((1260, 736, 1380, 820), fill="#af9584")
    d.rectangle((1301, 657, 1340, 767), fill="#c4a58b")
    d.polygon([(1293, 660), (1321, 625), (1348, 660)], fill="#30374a")
    d.line((1321, 625, 1321, 598), fill="#30374a", width=3)
    d.rectangle((1313, 686, 1327, 712), fill="#333e4b")
    d.polygon([(0, 950), (230, 920), (510, 973), (750, 1080), (0, 1080)], fill="#182a3a")
    return sign_landscape(image, "İSTANBUL / BOĞAZ")


def kapadokya() -> Image.Image:
    image = landscape_sky("#423549", "#f0b88c")
    d = ImageDraw.Draw(image)
    d.ellipse((1200, 210, 1440, 450), fill="#f8d7a2")
    for points, color in [
        ([(0, 650), (380, 570), (660, 630), (980, 485), (1250, 590), (1610, 470), (1920, 580), (1920, 1080), (0, 1080)], "#b27c74"),
        ([(0, 790), (330, 710), (770, 790), (1130, 640), (1460, 705), (1770, 600), (1920, 690), (1920, 1080), (0, 1080)], "#8b6265"),
    ]:
        d.polygon(points, fill=color)
    for x, y, h, w in ((640, 890, 250, 90), (840, 900, 330, 110), (1040, 860, 210, 90), (1250, 940, 380, 120), (1510, 930, 270, 100), (1730, 920, 350, 115)):
        d.polygon([(x - w, y), (x - w * .35, y - h * .75), (x, y - h), (x + w * .3, y - h * .75), (x + w, y)], fill="#d8a080")
        d.polygon([(x, y - h), (x + w * .3, y - h * .75), (x + w, y), (x + 15, y)], fill="#a36e64")
        d.polygon([(x - w * .6, y - h * .76), (x - 4, y - h - 14), (x + w * .6, y - h * .76)], fill="#5d4851")
        d.rounded_rectangle((x - 8, y - 95, x + 10, y - 64), radius=8, fill="#59454b")
    for x, y, r, color in ((990, 275, 40, RED), (1550, 335, 28, "#e5b07e"), (720, 390, 20, "#395d6b"), (1750, 200, 23, "#a44e5b")):
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)
        d.polygon([(x - r * .8, y + r * .55), (x - 6, y + r * 1.5), (x + 6, y + r * 1.5), (x + r * .8, y + r * .55)], fill=color)
        d.line((x - 7, y + r * 1.4, x - 5, y + r * 1.8), fill="#56454f", width=2)
        d.line((x + 7, y + r * 1.4, x + 5, y + r * 1.8), fill="#56454f", width=2)
        d.rectangle((x - 6, y + r * 1.8, x + 6, y + r * 1.95), fill="#56454f")
    d.polygon([(0, 920), (480, 860), (850, 995), (1150, 1080), (0, 1080)], fill="#4a3949")
    return sign_landscape(image, "KAPADOKYA / ŞAFAK")


def pamukkale() -> Image.Image:
    image = landscape_sky("#183c52", "#9bbdbe")
    d = ImageDraw.Draw(image)
    d.ellipse((1430, 150, 1610, 330), fill="#e5dbb5")
    d.polygon([(0, 580), (300, 490), (600, 570), (970, 435), (1310, 530), (1640, 420), (1920, 500), (1920, 1080), (0, 1080)], fill="#4a777e")
    # Traverten basamakları: beyaz kalsit kıyıları, turkuaz su aynaları.
    for index in range(9):
        y = 530 + index * 69
        edge = [(x, int(y + 34 * math.sin(x / 270 + index * .6))) for x in range(-50, 1980, 12)]
        d.polygon([*edge, (1980, 1080), (-50, 1080)], fill="#eee4ce" if index % 2 else "#d9d8cb")
        water = [(x, yy + 12) for x, yy in edge]
        lower = [(x, yy + 35 + index * 2) for x, yy in reversed(edge)]
        d.polygon([*water, *lower], fill="#61b6b9" if index % 2 else "#4798a5")
        d.line(edge, fill="#fff4dc", width=7)
    d.polygon([(0, 550), (130, 650), (250, 930), (600, 1080), (0, 1080)], fill="#294d5e")
    # Basit gölge, beyaz yüzey üzerinde alttaki yazıların kontrastını korur.
    d.polygon([(1370, 905), (1920, 880), (1920, 1080), (1370, 1080)], fill="#234956")
    return sign_landscape(image, "PAMUKKALE / TRAVERTEN")


def kackar() -> Image.Image:
    image = landscape_sky("#172c43", "#9bc1bb")
    d = ImageDraw.Draw(image)
    d.ellipse((1440, 140, 1600, 300), fill="#dce2cf")
    d.polygon([(0, 740), (240, 560), (520, 660), (860, 310), (1200, 630), (1450, 370), (1920, 690), (1920, 1080), (0, 1080)], fill="#627e89")
    d.polygon([(678, 500), (860, 310), (1050, 490), (920, 457), (852, 407), (795, 490), (755, 452)], fill="#d4dfd9")
    d.polygon([(1340, 474), (1450, 370), (1600, 475), (1500, 445), (1450, 421), (1395, 474)], fill="#c7d9d6")
    d.polygon([(0, 820), (420, 530), (780, 880), (1190, 620), (1510, 830), (1920, 650), (1920, 1080), (0, 1080)], fill="#2c6265")
    d.polygon([(0, 860), (380, 740), (800, 920), (1280, 760), (1920, 910), (1920, 1080), (0, 1080)], fill="#397376")
    d.polygon([(0, 1050), (400, 840), (820, 1060), (1390, 870), (1920, 1020), (1920, 1080), (0, 1080)], fill="#153f4b")
    for x in range(20, 1420, 52):
        y = 1010 + int(40 * math.sin(x / 160))
        h = 50 + (x * 7) % 85
        d.rectangle((x - 2, y - 20, x + 2, y + 15), fill="#152f3b")
        d.polygon([(x, y - h), (x - 26, y), (x + 26, y)], fill="#163b46")
    return sign_landscape(image, "KAÇKAR / YAYLALAR")


def anadolu() -> Image.Image:
    image = landscape_sky("#191b2b", "#262338")
    d = ImageDraw.Draw(image)
    colors = ("#a7354a", "#e1bb83", "#3e9395", "#795060")
    # Elibelinde ve baklava ritminden esinlenen özgün, geometrik bir yorum.
    for column in range(7):
        x = 690 + column * 195
        for row in range(-1, 6):
            y = row * 230 + (column % 2) * 115
            color = colors[(row + column) % len(colors)]
            d.polygon([(x, y - 85), (x + 72, y), (x, y + 85), (x - 72, y)], outline=color, width=6)
            d.polygon([(x, y - 47), (x + 39, y), (x, y + 47), (x - 39, y)], fill=color)
            d.line([(x - 88, y - 54), (x - 110, y - 31), (x - 88, y), (x - 110, y + 31), (x - 88, y + 54)], fill=color, width=4)
    # Deseni sağda yoğunlaştır; masaüstü simgelerinin solu sakin kalır.
    shade = Image.new("RGBA", image.size)
    sd = ImageDraw.Draw(shade)
    for x in range(1920):
        sd.line((x, 0, x, 1080), fill=(19, 22, 32, max(0, int(220 * (1 - x / 1200)))))
    image = Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB")
    d = ImageDraw.Draw(image)
    d.rectangle((1400, 925, 1900, 1045), fill="#191d2d")
    return sign_landscape(image, "ANADOLU / KİLİM")


def render_wallpapers(root: Path) -> None:
    entries = []
    gallery = (
        ("ay-yildiz", "Ay Yıldız", "wallpaper.png", wallpaper),
        ("istanbul", "İstanbul · Boğaz", "istanbul.png", istanbul),
        ("kapadokya", "Kapadokya · Şafak", "kapadokya.png", kapadokya),
        ("pamukkale", "Pamukkale · Traverten", "pamukkale.png", pamukkale),
        ("kackar", "Kaçkar · Yaylalar", "kackar.png", kackar),
        ("anadolu", "Anadolu · Kilim", "anadolu.png", anadolu),
    )
    for identifier, name, filename, factory in gallery:
        image = factory()
        path = "/usr/share/backgrounds/oguzdows/" + filename
        preview = "/usr/share/oguzdows/wallpaper-previews/" + filename
        save(image, root, path)
        save(image.resize((320, 180), Image.Resampling.LANCZOS), root, preview)
        entries.append({"id": identifier, "name": name, "path": path, "preview": preview})
    photographs = (
        ("bogaz-sabahi", "Boğaz · Sabah Işığı"),
        ("kackar-sisi", "Kaçkar · Sis Denizinde"),
        ("kapadokya-isigi", "Kapadokya · Gün Doğumu"),
        ("oludeniz-kiyisi", "Ölüdeniz · Turkuaz Kıyı"),
        ("tuz-golu-aksami", "Tuz Gölü · Akşam Aynası"),
        ("ani-kisi", "Ani · Kış Sessizliği"),
    )
    for identifier, name in photographs:
        relative = "usr/share/backgrounds/oguzdows/" + identifier + ".jpg"
        source = root / relative
        if not source.is_file():
            source = Path(__file__).resolve().parents[1] / "system" / relative
        target_image = root / relative
        target_image.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target_image.resolve():
            shutil.copyfile(source, target_image)
        with Image.open(source) as image:
            preview = "/usr/share/oguzdows/wallpaper-previews/" + identifier + ".jpg"
            save(image.resize((320, 180), Image.Resampling.LANCZOS), root, preview)
        entries.append({"id": identifier, "name": name, "path": "/" + relative, "preview": preview, "origin": "AI-generated"})
    target = root / "usr/share/oguzdows/wallpapers.json"
    target.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
        color = "#e1e6ef" if state == "inactive" else PAPER
        for button in ("close", "hide", "maximize", "maximize-toggled", "menu"):
            # Eski GPU'da da bütün düğme döşemesi tamamen opaktır.
            image = Image.new("RGBA", (28 * 3, 32 * 3), "#191c24" if state == "inactive" else "#1c202a")
            draw = ImageDraw.Draw(image)
            if button == "close" or state in ("prelight", "pressed"):
                fill = ("#9f293e" if state == "inactive" else RED) if button == "close" else "#37424b"
                draw.rounded_rectangle((6, 12, 78, 84), radius=15, fill=fill)
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
inactive_text_color=#d4dce8
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


def nazar(level: int, size: int = 48, charging: bool = False) -> Image.Image:
    """Mavi cam boncuk aşağıdan yukarı açılır; güç politikası değişmez."""
    level = max(0, min(100, level))
    n = size * 3
    image = Image.new("RGBA", (n, n))
    for y in range(n):
        for x in range(n):
            r = math.hypot(x - n * .47, y - n * .5) / (n * .43)
            if r > 1:
                continue
            if y < n * (1 - level / 100):
                color = (48, 57, 74, 255)
            else:
                color = (9, 64, 178) if r > .70 else ((245, 242, 216) if r > .46 else ((52, 179, 227) if r > .23 else (9, 22, 39)))
                glow = 1 - .30 * r + .12 * (1 - y / n)
                color = tuple(min(255, round(channel * glow)) for channel in color) + (255,)
            image.putpixel((x, y), color)
    draw = ImageDraw.Draw(image)
    if level:
        draw.arc((n*.1, n*.12, n*.8, n*.88), 195, 250, fill=(200, 237, 255, 220), width=max(1, n//30))
    if charging:
        draw.polygon([(n*.79,n*.08),(n*.64,n*.43),(n*.77,n*.43),(n*.68,n*.70),(n*.96,n*.33),(n*.82,n*.33),(n*.94,n*.08)], fill="#ffda71", outline="#3e331d", width=max(1,n//48))
    elif level <= 10:
        draw.ellipse((n*.65,n*.64,n*.97,n*.96), fill="#d63c53")
        draw.line((n*.81,n*.69,n*.81,n*.83), fill="white", width=max(2,n//24))
        draw.ellipse((n*.79,n*.87,n*.83,n*.91), fill="white")
    return image.resize((size, size), Image.Resampling.LANCZOS)


def power_fallback(size: int, missing: bool) -> Image.Image:
    # Yeni ikon tabanlarında kaldırılan durumlar boş pil gibi gösterilmez.
    n = size * 3
    image = Image.new("RGBA", (n, n))
    draw = ImageDraw.Draw(image)
    color = "#d6e1ed"
    line = max(2, n // 18)
    if missing:
        draw.rounded_rectangle((n*.23,n*.17,n*.76,n*.91), radius=n*.06, outline=color, width=line)
        draw.rectangle((n*.39,n*.08,n*.60,n*.18), fill=color)
        draw.text((n*.50,n*.53), "?", font=font(round(n*.43), True), fill=color, anchor="mm")
    else:
        for x in (.35, .64):
            draw.line((n*x,n*.10,n*x,n*.38), fill=color, width=line)
        draw.rounded_rectangle((n*.23,n*.32,n*.77,n*.66), radius=n*.12, outline=color, width=line)
        draw.line([(n*.50,n*.66),(n*.50,n*.87),(n*.76,n*.87)], fill=color, width=line)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def render_nazar(root: Path) -> None:
    sizes = (16, 24, 32, 48)
    base = root / "usr/share/icons/OguzDows"
    base.mkdir(parents=True, exist_ok=True)
    directories = [f"{size}x{size}/status" for size in sizes]
    index = "[Icon Theme]\nName=OguzDows\nComment=Nazar boncuğu pil göstergeleri\nInherits=Adwaita,hicolor\nDirectories=" + ",".join(directories) + "\n"
    for size, directory in zip(sizes, directories):
        index += f"\n[{directory}]\nSize={size}\nContext=Status\nType=Fixed\n"
        for level in range(0, 101, 10):
            # Xfce son dilimde 100 adını kullanır; tam dolu durumu ayrı ikondur.
            shown = min(level, 95)
            for suffix, charging in (("", False), ("-charging", True)):
                image = nazar(shown, size, charging)
                for name in (f"battery-level-{level}{suffix}-symbolic", f"battery-level-{level}{suffix}", f"xfpm-primary-{level:03}{suffix}"):
                    save(image, root, f"usr/share/icons/OguzDows/{directory}/{name}.png")
        for name, level in (("empty", 0), ("caution", 10), ("low", 20), ("good", 60), ("full", 95), ("full-charged", 100)):
            for suffix in ("", "-symbolic"):
                save(nazar(level, size), root, f"usr/share/icons/OguzDows/{directory}/battery-{name}{suffix}.png")
                save(nazar(level, size, True), root, f"usr/share/icons/OguzDows/{directory}/battery-{name}-charging{suffix}.png")
        for name in ("battery-level-100-charged-symbolic", "battery-level-100-charged", "xfpm-primary-charged"):
            save(nazar(100, size), root, f"usr/share/icons/OguzDows/{directory}/{name}.png")
        for name, missing in (("battery-missing", True), ("ac-adapter", False)):
            for suffix in ("", "-symbolic"):
                save(power_fallback(size, missing), root, f"usr/share/icons/OguzDows/{directory}/{name}{suffix}.png")
    (base / "index.theme").write_text(index, encoding="utf-8")


def render(root: Path) -> None:
    render_wallpapers(root)
    render_nazar(root)
    source = Path(__file__).resolve().parents[1] / "system/usr/share/oguzdows/rifki"
    target = root / "usr/share/oguzdows/rifki"
    if source.is_dir() and source.resolve() != target.resolve():
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("rig", "envelopes.json", "intro-full.wav", "hello.wav", "help.wav", "disk.wav", "talk-blink.png"))
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
