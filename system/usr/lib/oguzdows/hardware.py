"""GUI ve yetkili sürücü yardımcısının paylaştığı salt-okunur donanım mantığı."""
from __future__ import annotations

import datetime
import os
import platform
import subprocess
from pathlib import Path

# Broadcom STA'nın desteklediği PCI kimlikleri. Diğer Broadcom aygıtları için
# b43 / brcmsmac / brcmfmac yerleşik sürücüleri korunur.
BROADCOM_STA_IDS = frozenset({
    "4311", "4312", "4313", "4315", "4328", "4329", "432a", "432b", "432c",
    "432d", "4353", "4357", "4358", "4359", "4360", "4365", "43a0", "43b1",
})


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def is_live(cmdline: str | None = None) -> bool:
    return "boot=live" in (read_text(Path("/proc/cmdline")) if cmdline is None else cmdline).split()


def memory_kib(meminfo: str | None = None) -> int:
    text = read_text(Path("/proc/meminfo")) if meminfo is None else meminfo
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            try:
                return max(0, int(line.split()[1]))
            except (ValueError, IndexError):
                return 0
    return 0


def light_profile(cmdline: str, memory: int) -> bool:
    args = cmdline.split()
    return "oguzdows.profile=light" in args or "nomodeset" in args or 0 < memory <= 2097152


def supported_broadcom(sysfs: Path = Path("/sys/bus/pci/devices")) -> list[str]:
    devices = []
    for path in sorted(sysfs.glob("*")):
        vendor = read_text(path / "vendor").strip().lower()
        device = read_text(path / "device").strip().lower().removeprefix("0x")
        # Ağ denetleyicisi dışında aynı sayısal kimliğe bakarak karar verme.
        device_class = read_text(path / "class").strip().lower()
        if vendor == "0x14e4" and device in BROADCOM_STA_IDS and device_class.startswith("0x02"):
            devices.append(f"14e4:{device}")
    return devices


def command_output(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=12,
                                env={**os.environ, "LC_ALL": "C", "LANG": "C"}, check=False)
    except FileNotFoundError:
        return "Bu tanılama aracı kurulu değil."
    except subprocess.TimeoutExpired:
        return "Donanım sorgusu zaman aşımına uğradı."
    except OSError:
        return "Donanım bilgisi okunamadı."
    return (result.stdout.strip() or "Aygıt bilgisi alınamadı.")[:60000]


def report() -> str:
    memory = memory_kib()
    cmdline = read_text(Path("/proc/cmdline"))
    sections = [
        "OğuzDows · Donanım ve Sürücüler",
        datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        f"Mimari: {platform.machine()}   Çekirdek: {platform.release()}",
        f"Bellek: {memory // 1024} MiB",
        "Oturum: " + ("Canlı OğuzDows" if is_live(cmdline) else "Kurulu OğuzDows"),
        "Profil: " + ("Hafif / efektler kapalı" if light_profile(cmdline, memory) else "Standart"),
        "\nPCI aygıtları ve kullanılan çekirdek sürücüleri\n" + command_output(["/usr/bin/lspci", "-nnk"]),
        "\nUSB aygıtları\n" + command_output(["/usr/bin/lsusb"]),
        "\nKablosuz anahtarları\n" + command_output(["/usr/sbin/rfkill", "list"]),
        "\nNot: Bu rapor yerel olarak üretilir; hiçbir yere gönderilmez.",
    ]
    return "\n".join(sections) + "\n"
