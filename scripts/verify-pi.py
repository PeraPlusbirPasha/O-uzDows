#!/usr/bin/env python3
"""Bağlanmış Pi kökünü ve boot dosyalarını denetler; bu bir kart açılış testi değildir."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8", errors="replace")


def validate(root: Path, arch: str, pre_export: bool = False) -> None:
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    info = json.loads(read(root, "etc/oguzdows/pi-image.json"))
    lock = json.loads(read(root, "usr/share/oguzdows/pi-gen.lock.json"))
    require(info["arch"] == arch and info["platform"] == "raspberrypi", "Yanlış Pi mimarisi / platformu.")
    require(info["pi_gen_commit"] == lock[arch]["commit"], "pi-gen kaynak kimliği uyuşmuyor.")
    files = ["boot/firmware/config.txt", "boot/firmware/cmdline.txt", "boot/firmware/start.elf",
             "boot/firmware/start4.elf", "boot/firmware/fixup.dat", "boot/firmware/bootcode.bin",
             "boot/firmware/overlays/vc4-kms-v3d.dtbo", "usr/share/xsessions/oguzdows.desktop",
             "usr/share/backgrounds/oguzdows/wallpaper.png", "usr/share/oguzdows/wallpapers.json",
             "usr/share/themes/OguzDows/xfwm4/themerc", "usr/lib/oguzdows/pi-firstboot.py",
             "etc/systemd/system/lightdm.service.d/10-oguzdows-firstboot.conf",
             "etc/systemd/system/ssh.service.d/10-oguzdows-firstboot.conf"]
    for filename in lock[arch]["kernels"] + lock[arch]["dtbs"] + ([] if pre_export else lock[arch]["initramfs"]):
        files.append("boot/firmware/" + filename)
    for filename in files:
        path = root / filename
        require(path.is_file() and path.stat().st_size > 0, "Eksik / boş Pi dosyası: " + filename)
    config = read(root, "boot/firmware/config.txt")
    require("dtoverlay=vc4-kms-v3d" in config and "auto_initramfs=1" in config, "KMS / initramfs algılama eksik.")
    require("arm_64bit=1" in config if arch == "arm64" else "arm_64bit=1" not in config, "Yanlış firmware bit modu.")
    require(not re.search(r"(?m)^\s*(over_voltage\w*|force_turbo|arm_freq)\s*=", config), "Zorunlu overclock bulundu.")
    cmdline = read(root, "boot/firmware/cmdline.txt")
    args = cmdline.split()
    require(len(cmdline.strip().splitlines()) == 1, "cmdline.txt tek satır olmalı.")
    require(any(re.fullmatch(r"root=PARTUUID=[0-9a-fA-F]{8}-02", arg) for arg in args), "Kök PARTUUID çözülmedi.")
    require("ROOTDEV" not in cmdline and "BOOTDEV" not in read(root, "etc/fstab"), "Bölüm yer tutucusu kaldı.")
    require("boot=live" not in args and not any("username=oguz" == arg for arg in args), "Canlı PC hesabı taşındı.")
    require("OğuzDows" in read(root, "usr/lib/os-release"), "Ürün kimliği eksik.")
    for filename in ("etc/systemd/system/oguzdows-live-setup.service", "usr/local/sbin/oguzdows-installer",
                     "etc/calamares", "var/lib/oguzdows/firstboot.done", "var/lib/oguzdows/firstboot.pending.json"):
        require(not (root / filename).exists(), "Dağıtıma taşınmaması gereken dosya: " + filename)
    require(not any(1000 <= int(line.split(":")[2]) < 60000 for line in read(root, "etc/passwd").splitlines()),
            "İmajda önceden oluşturulmuş normal kullanıcı var.")
    shadow = {line.split(":")[0]: line.split(":")[1] for line in read(root, "etc/shadow").splitlines()}
    require(shadow.get("root", "").startswith(("!", "*")), "Root hesabı kilitli değil.")
    for filename in [root / "etc/sudoers", *(root / "etc/sudoers.d").glob("*")]:
        if filename.is_file():
            require(not any("NOPASSWD" in line.partition("#")[0] for line in filename.read_text().splitlines()),
                    "Kalıcı imajda parolasız sudo kuralı var: " + filename.name)
    for filename in (root / "etc/lightdm").rglob("*.conf"):
        require(not any(re.match(r"\s*autologin-user\s*=\s*\S", line.partition("#")[0])
                        for line in filename.read_text().splitlines()), "Kalıcı imajda otomatik giriş açık.")
    for service in ("oguzdows-pi-firstboot", "oguzdows-pi-tune", "zramswap"):
        require((root / f"etc/systemd/system/multi-user.target.wants/{service}.service").is_symlink(),
                "Servis etkinleştirilmemiş: " + service)
    require((root / "etc/systemd/system/display-manager.service").is_symlink()
            and (root / "etc/systemd/system/display-manager.service").readlink().name == "lightdm.service", "LightDM varsayılan değil.")
    require(not (root / "etc/systemd/system/multi-user.target.wants/ssh.service").is_symlink(), "SSH varsayılan olarak açık.")
    require((root / "etc/systemd/system/dphys-swapfile.service").is_symlink()
            and (root / "etc/systemd/system/dphys-swapfile.service").readlink() == Path("/dev/null"), "SD swap devre dışı değil.")
    require(not list((root / "etc/ssh").glob("ssh_host_*_key*")), "Kopyalanmış SSH sunucu anahtarı var.")
    if not pre_export:
        require(not read(root, "etc/machine-id").strip(), "Makine kimliği sıfırlanmamış.")
    print(f"OğuzDows Pi {arch}: dosya / boot / hesap güvenliği doğrulandı ({'export öncesi' if pre_export else 'son imaj'}).")
    print("Bu sonuç fiziksel Pi açılışı, çevre birimi veya performans doğrulaması değildir.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--arch", choices=("armhf", "arm64"), required=True)
    parser.add_argument("--pre-export", action="store_true")
    args = parser.parse_args()
    validate(args.root.resolve(), args.arch, args.pre_export)


if __name__ == "__main__":
    main()
