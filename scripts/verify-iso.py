#!/usr/bin/env python3
"""ISO'yu açmadan önce önyükleme dosyalarının marka/menü sözleşmesini doğrular.

Bu kontrol sanal makinede açılış veya fiziksel donanım testi yerine geçmez.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path


def validate_tree(root: Path, arch: str) -> set[str]:
    bios_file = root / "isolinux/isolinux.cfg"
    bios = bios_file.read_text(encoding="ascii")
    labels = re.findall(r"^LABEL (\S+)$", bios, re.MULTILINE)
    expected = ["oguzdows", "oguzdows-safe", "oguzdows-light", "oguzdows-verbose"]
    if labels != expected or "DEFAULT oguzdows\n" not in bios:
        raise ValueError("OğuzDows BIOS seçimleri eksik veya sıraları yanlış.")
    if "nomodeset" not in bios or "oguzdows.profile=light" not in bios:
        raise ValueError("Eski donanım seçenekleri eksik.")
    paths = set(re.findall(r"^  (?:LINUX|INITRD) (\S+)$", bios, re.MULTILINE))
    if len(paths) != 2 or not all(path.startswith("/live/") for path in paths):
        raise ValueError("Çekirdek/initrd yolları geçersiz.")
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in (".cfg", ".txt", ".svg"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "debian" in text or "@linux@" in text or "@initrd@" in text:
                raise ValueError(f"Varsayılan marka veya çözülmemiş şablon bulundu: {path.name}")
    if "OğuzDows" not in (root / ".disk/info").read_text():
        raise ValueError("ISO kimliği OğuzDows değil.")
    if arch == "amd64":
        grub = (root / "boot/grub/grub.cfg").read_text()
        if len(re.findall(r"^menuentry ", grub, re.MULTILINE)) != 4 or "OğuzDows'u başlat" not in grub:
            raise ValueError("OğuzDows UEFI menüsü eksik.")
        for path in paths:
            if path not in grub:
                raise ValueError("BIOS ve UEFI çekirdek yolları uyuşmuyor.")
        if not (root / "boot/grub/oguzdows-theme.txt").is_file():
            raise ValueError("UEFI teması eksik.")
    return paths


def verify(iso: Path, arch: str) -> None:
    with tempfile.TemporaryDirectory(prefix="oguzdows-iso-") as directory:
        root = Path(directory)
        command = ["xorriso", "-abort_on", "FAILURE", "-return_with", "SORRY", "32",
                   "-osirrox", "on", "-indev", str(iso.resolve()),
                   "-extract", "/isolinux", str(root / "isolinux"),
                   "-extract", "/.disk/info", str(root / ".disk/info")]
        (root / ".disk").mkdir()
        if arch == "amd64":
            (root / "boot").mkdir()
            command += ["-extract", "/boot/grub", str(root / "boot/grub")]
        subprocess.run(command, check=True, capture_output=True, text=True)
        paths = validate_tree(root, arch)
        if arch == "amd64":
            paths.add("/EFI/boot/bootx64.efi")
        subprocess.run(["xorriso", "-abort_on", "FAILURE", "-return_with", "SORRY", "32",
                        "-indev", str(iso.resolve()), "-ls", *sorted(paths), "--"],
                       check=True, capture_output=True, text=True)
    print(f"OğuzDows {arch}: ISO menüleri, marka ve önyükleme dosyaları doğrulandı.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("--arch", choices=("amd64", "i386"), required=True)
    args = parser.parse_args()
    try:
        verify(args.iso, args.arch)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"ISO doğrulaması başarısız: {error}\n")


if __name__ == "__main__":
    main()
