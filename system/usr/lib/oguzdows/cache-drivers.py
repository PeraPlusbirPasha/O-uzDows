#!/usr/bin/python3 -I
"""Yalnızca ISO derlemesinde: ek sürücü arşivlerini ve lisanslarını saklar."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/usr/lib/oguzdows")
from offline import DIRECTORY, PACKAGES


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def cache(directory: Path = DIRECTORY, modules: Path = Path("/lib/modules")) -> None:
    kernels = sorted(path for path in modules.iterdir() if (path / "modules.dep").is_file())
    if not kernels:
        raise RuntimeError("ISO çekirdeği bulunamadı; çevrimdışı sürücü deposu oluşturulmadı.")
    for kernel in kernels:
        if not (kernel / "build/Makefile").is_file():
            raise RuntimeError("Çekirdekle eşleşen başlıklar eksik: " + kernel.name)
    directory.mkdir(parents=True, exist_ok=True)
    licenses = directory / "licenses"
    licenses.mkdir(exist_ok=True)
    manifest = {"format": 1, "kernels": [kernel.name for kernel in kernels], "packages": {}}
    env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C.UTF-8"}
    for package in PACKAGES.values():
        # apt-get download, imzalı paket dizinlerindeki SHA-256'yı doğrular.
        # Depo doğrulamasını kapatan bir seçenek veya harici URL kullanılmaz.
        run(["/usr/bin/apt-get", "-o", "APT::Sandbox::User=root", "download", package], cwd=directory, env=env)
        archives = sorted(directory.glob(package + "_*.deb"))
        if len(archives) != 1:
            raise RuntimeError("Tek bir sürücü paketi bekleniyordu: " + package)
        archive = archives[0]
        fields = run(["/usr/bin/dpkg-deb", "-f", str(archive), "Package", "Version"], capture_output=True, text=True).stdout
        if "Package: " + package + "\n" not in fields:
            raise RuntimeError("Paket kimliği eşleşmiyor: " + package)
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        with tempfile.TemporaryDirectory(prefix="oguzdows-license-") as temporary:
            run(["/usr/bin/dpkg-deb", "-x", str(archive), temporary])
            copyright = Path(temporary) / "usr/share/doc" / package / "copyright"
            if copyright.is_file():
                text = copyright.read_text(encoding="utf-8", errors="replace")
            elif copyright.with_suffix(".gz").is_file():
                with gzip.open(copyright.with_suffix(".gz"), "rt", encoding="utf-8", errors="replace") as stream:
                    text = stream.read()
            else:
                raise RuntimeError("Sürücü lisansı bulunamadı: " + package)
            (licenses / (package + ".txt")).write_text(text, encoding="utf-8")
        # Sadece çözümleme: kurulum/postinst/lisans kabulü çalıştırılmaz.
        # Gerekli bağımlılıklar ISO'da yoksa internet gerektiren bir imaj üretme.
        run(["/usr/bin/apt-get", "--simulate", "--no-download", "--no-remove", "--no-install-recommends", "install", str(archive)], env=env)
        manifest["packages"][package] = {"filename": archive.name, "sha256": digest, "metadata": fields}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for path in directory.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)
    print("Çevrimdışı sürücüler, özgün lisansları ve eşleşen çekirdek başlıkları hazır.")


if __name__ == "__main__":
    if os.geteuid() != 0:
        raise SystemExit("Bu hazırlık yalnızca ISO derleme chroot'unda çalıştırılır.")
    cache()
