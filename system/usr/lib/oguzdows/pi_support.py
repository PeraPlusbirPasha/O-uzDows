"""Pi algılama ve kaynak politikası; donanıma yazmaz, PC'de de içe aktarılabilir."""
from __future__ import annotations

import json
import platform
from pathlib import Path


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").replace("\x00", "").strip()
    except OSError:
        return ""


def model(root: Path = Path("/")) -> str:
    return text(root / "sys/firmware/devicetree/base/model") or text(root / "proc/device-tree/model")


def is_pi(root: Path = Path("/")) -> bool:
    return (root / "etc/oguzdows/pi-image.json").is_file() or model(root).startswith("Raspberry Pi")


def armv6(machine: str | None = None, board: str | None = None) -> bool:
    machine = platform.machine() if machine is None else machine
    board = model() if board is None else board
    # 64-bit kernel üzerinde 32-bit kullanıcı alanı mümkün; kart adı da önemlidir.
    return machine.startswith("armv6") or (
        board.startswith(("Raspberry Pi Zero", "Raspberry Pi 1 ", "Raspberry Pi Model ", "Raspberry Pi Compute Module Rev"))
        and not board.startswith("Raspberry Pi Zero 2")
    )


def policy(memory_kib: int, board: str, requested: str = "auto") -> dict:
    if requested not in ("auto", "mini", "light", "full"):
        raise ValueError("Profil auto, mini, light veya full olmalı.")
    legacy = armv6("", board)
    if requested == "auto":
        profile = "mini" if legacy or 0 < memory_kib <= 786432 else "light" if 0 < memory_kib <= 2097152 else "full"
    else:
        profile = requested
    # Zram gerçek RAM'den büyük ayrılmaz; kullanıcı 'full' seçse de kapasite güvenli.
    usable_mb = max(1, memory_kib // 1024) if memory_kib > 0 else 512
    zram_mb = min(usable_mb, max(64, min(384 if profile == "mini" else 1024,
                                      usable_mb * (75 if profile == "mini" else 50) // 100)))
    return {"profile": profile, "compositing": profile == "full", "animations": profile == "full",
            "zram_mb": zram_mb, "algorithm": "lz4", "swappiness": 100, "page_cluster": 0}


def current_policy(root: Path = Path("/")) -> dict:
    memory = 0
    for line in text(root / "proc/meminfo").splitlines():
        if line.startswith("MemTotal:"):
            try:
                memory = max(0, int(line.split()[1]))
            except (ValueError, IndexError):
                pass
    requested = "auto"
    # Dosya shell olarak çalıştırılmaz; yalnızca bilinen anahtar/değerler okunur.
    for line in text(root / "etc/oguzdows/pi.conf").splitlines():
        key, sep, value = line.partition("#")[0].strip().partition("=")
        if sep and key.strip() == "profile":
            requested = value.strip()
    for arg in text(root / "proc/cmdline").split():
        if arg.startswith("oguzdows.profile="):
            requested = arg.partition("=")[2]
    if requested not in ("auto", "mini", "light", "full"):
        requested = "auto"  # Hatalı ayar, açılışı engellemesin.
    return policy(memory, model(root), requested)


def peripheral_summary(root: Path = Path("/sys")) -> str:
    lines = []
    # Pi Wi-Fi SDIO'dur, VC4/V3D ise platform aygıtıdır; PCI araması yeterli değil.
    for bus in ("sdio", "platform"):
        for device in sorted((root / "bus" / bus / "devices").glob("*")):
            driver_link = device / "driver"
            driver = driver_link.resolve().name if driver_link.is_symlink() else "SÜRÜCÜ BAĞLI DEĞİL"
            identity = text(device / "modalias")
            if bus == "sdio" or any(key in (device.name + " " + driver + " " + identity).lower()
                                     for key in ("vc4", "v3d", "gpu", "hdmi", "bcm2835", "brcm", "rp1", "mmc")):
                lines.append(f"{bus} · {device.name} → {driver}")
    for interface in sorted((root / "class/net").glob("*")):
        if interface.name == "lo":
            continue
        link = interface / "device/driver"
        driver = link.resolve().name if link.is_symlink() else "SÜRÜCÜ BAĞLI DEĞİL / sanal aygıt"
        lines.append(f"Ağ · {interface.name} → {driver}")
    for card in sorted((root / "class/drm").glob("card[0-9]*")):
        if "-" in card.name:
            continue
        link = card / "device/driver"
        driver = link.resolve().name if link.is_symlink() else "SÜRÜCÜ BAĞLI DEĞİL"
        lines.append(f"DRM · {card.name} → {driver}")
    return "\n".join(lines) or "Platform / SDIO aygıtı bulunamadı."


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()
    settings = current_policy()
    print(settings["profile"] if args.profile else json.dumps(settings, ensure_ascii=False, indent=2))
