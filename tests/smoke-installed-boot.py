#!/usr/bin/env python3
"""Yalnızca geçici disk imajlarında gerçek GRUB → BIOS/UEFI açılış kontrolü.

İşletim sistemi/çekirdek kurmaz. 'No bootable device' öncesindeki firmware ve
GRUB aşamasını sınar; hiçbir fiziksel disk adı kabul etmez.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    print("+", *map(str, args), flush=True)
    subprocess.run(list(map(str, args)), check=True, timeout=120)


def firmware_files(work: Path) -> list[str]:
    for suffix in ("_4M", ""):
        code = Path(f"/usr/share/OVMF/OVMF_CODE{suffix}.fd")
        variables = Path(f"/usr/share/OVMF/OVMF_VARS{suffix}.fd")
        if code.is_file() and variables.is_file():
            nvram = work / "fresh-nvram.fd"
            shutil.copy2(variables, nvram)
            return ["-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                    "-drive", f"if=pflash,format=raw,file={nvram}"]
    raise RuntimeError("OVMF firmware dosyaları kurulu değil.")


def boot_vm(image: Path, mode: str, output: Path, work: Path) -> None:
    serial = output / f"installed-{mode}.serial.log"
    marker = f"OGUZDOWS-INSTALLED-{mode.upper()}-OK"
    args = ["qemu-system-x86_64", "-machine", "pc,accel=tcg", "-m", "192",
            "-display", "none", "-monitor", "none", "-serial", f"file:{serial}",
            "-drive", f"file={image},format=raw,if=ide,snapshot=on", "-nic", "none", "-boot", "c", "-no-reboot"]
    if mode == "efi":
        args += firmware_files(work)
    with (output / f"installed-{mode}.qemu.log").open("w") as log:
        process = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                text = serial.read_text(errors="replace") if serial.exists() else ""
                if marker in text:
                    print(f"{mode}: firmware diski buldu ve kurulu GRUB menüsünü okudu.", flush=True)
                    return
                if process.poll() is not None:
                    raise RuntimeError(f"{mode}: QEMU erken kapandı: {text[-4000:]}")
                time.sleep(0.2)
            raise RuntimeError(f"{mode}: GRUB seri işareti 60 saniyede görünmedi: {text[-4000:]}")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def partition_device(loop: str, number: int) -> str:
    device = f"{loop}p{number}"
    # Privileged container'da host udev, container'ın özel /dev alanını doldurmayabilir.
    major, minor = map(int, (Path("/sys/class/block") / Path(device).name / "dev").read_text().split(":"))
    expected = os.makedev(major, minor)
    if not Path(device).exists():
        os.mknod(device, stat.S_IFBLK | 0o600, expected)
    info = os.stat(device)
    if not stat.S_ISBLK(info.st_mode) or info.st_rdev != expected:
        raise RuntimeError("Geçici loop bölüm düğümü eşleşmiyor: " + device)
    return device


def check_mode(module, mode: str, output: Path) -> None:
    work = Path(tempfile.mkdtemp(prefix=f"oguzdows-boot-{mode}-"))
    image = work / "private-test-disk.img"
    target = work / "target"
    target.mkdir()
    loop = None
    mounts = []
    try:
        with image.open("wb") as stream:
            stream.truncate(192 * 1024 * 1024)
        if mode == "bios":
            run("parted", "--script", image, "mklabel", "msdos", "mkpart", "primary", "ext4", "1MiB", "100%")
        else:
            run("parted", "--script", image, "mklabel", "gpt", "mkpart", "ESP", "fat32", "1MiB", "65MiB",
                "set", "1", "esp", "on", "mkpart", "primary", "ext4", "65MiB", "100%")
        allocated = subprocess.check_output(["losetup", "--find", "--show", "--partscan", str(image)], text=True).strip()
        # Hiçbir zaman host /dev/sda vb. üzerinde işlem yapılamaz.
        if not re.fullmatch(r"/dev/loop[0-9]+", allocated):
            raise RuntimeError("Beklenmeyen loop aygıtı: " + allocated)
        backing = Path("/sys/class/block") / Path(allocated).name / "loop/backing_file"
        if Path(backing.read_text().strip()).resolve() != image.resolve():
            raise RuntimeError("Loop aygıtı bu testin özel imajına bağlı değil; işlem yapılmadı.")
        loop = allocated
        root_partition = partition_device(loop, 1 if mode == "bios" else 2)
        run("mkfs.ext4", "-F", "-q", root_partition)
        run("mount", root_partition, target)
        mounts.append(target)
        (target / "boot/grub").mkdir(parents=True)
        parts = [{"device": root_partition, "mountPoint": "/", "fs": "ext4"}]
        boot_loader = {"installPath": loop} if mode == "bios" else None
        if mode == "efi":
            esp = target / "boot/efi"
            esp.mkdir()
            esp_device = partition_device(loop, 1)
            run("mkfs.fat", "-F", "32", esp_device)
            run("mount", esp_device, esp)
            mounts.append(esp)
            parts.append({"device": esp_device, "mountPoint": "/boot/efi", "fs": "fat32"})
        module.check(target, mode, parts, boot_loader, "prepare")
        command = ["grub-install", "--target=" + ("i386-pc" if mode == "bios" else "x86_64-efi"),
                   "--boot-directory=" + str(target / "boot"), "--recheck", "--force"]
        if mode == "bios":
            command.append(loop)
        else:
            command += ["--efi-directory=" + str(target / "boot/efi"), "--bootloader-id=OguzDows", "--no-nvram"]
        run(*command)
        if mode == "efi":
            # Calamares installEFIFallback=true ile aynı dosya yolu; NVRAM girişi yok.
            fallback = target / "boot/efi/EFI/BOOT/BOOTX64.EFI"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target / "boot/efi/EFI/OguzDows/grubx64.efi", fallback)
        menu = target / "boot/grub/grub.cfg"
        menu.write_text("serial --unit=0 --speed=115200\nterminal_output serial\n"
                        + f"echo OGUZDOWS-INSTALLED-{mode.upper()}-OK\nhalt\n"
                        + "menuentry 'OğuzDows çekirdek kurmayan boot testi' {\n linux /boot/test-only-not-a-kernel\n}\n")
        with image.open("rb") as stream:
            before_mbr = stream.read(512)
        module.check(target, mode, parts, boot_loader, "verify")
        with image.open("rb") as stream:
            after_mbr = stream.read(512)
        changed = [i for i, pair in enumerate(zip(before_mbr, after_mbr)) if pair[0] != pair[1]]
        if mode == "bios":
            if changed not in ([], [446]) or after_mbr[446] != 0x80:
                raise RuntimeError("BIOS MBR tek-bayt sınırı ihlal edildi.")
        elif changed:
            raise RuntimeError("UEFI yolunda MBR değiştirildi.")
        while mounts:
            run("umount", mounts[-1])
            mounts.pop()
        run("losetup", "--detach", loop)
        loop = None
        boot_vm(image, mode, output, work)
    finally:
        # Bağlı bir dosya sistemi üzerinde otomatik rm/rmtree yapılmaz.
        safe_to_remove = True
        for mount in reversed(mounts):
            if subprocess.run(["umount", str(mount)], check=False).returncode != 0:
                safe_to_remove = False
        if os.path.ismount(target) or os.path.ismount(target / "boot/efi"):
            safe_to_remove = False
        if loop and safe_to_remove:
            safe_to_remove = subprocess.run(["losetup", "--detach", loop], check=False).returncode == 0
        if safe_to_remove:
            shutil.rmtree(work)
        else:
            print("Bağlı test alanı korundu, otomatik silinmedi: " + str(work), file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("test-results/installed-boot"))
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Geçici loop disk / mount testi için izole root ortamı gerekli.")
    args.output.mkdir(parents=True, exist_ok=True)
    sys.modules["libcalamares"] = SimpleNamespace(utils=SimpleNamespace(debug=lambda text: print(text, flush=True)))
    spec = importlib.util.spec_from_file_location("oguzdows_boot_check", ROOT / "installer/modules/oguzdowsboot/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for mode in ("bios", "efi"):
        check_mode(module, mode, args.output.resolve())
    print("Gerçek GRUB BIOS ve UEFI fallback açılışı geçti. Bu tam OS kurulumu/fiziksel PC testi değildir.")


if __name__ == "__main__":
    main()
