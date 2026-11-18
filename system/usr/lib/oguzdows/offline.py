"""ISO'ya gömülü, imzalı depodan alınmış ek sürücü paketleri.

İndirme yalnızca ISO derlenirken yapılır. Kullanıcı işlemi sabit bir izin
listesinden seçer; arşiv bütünlüğü kurulumdan önce tekrar denetlenir.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

DIRECTORY = Path("/usr/share/oguzdows/offline-drivers")
CHOICES = Path("/run/oguzdows/selected-drivers.json")
PACKAGES = {
    "broadcom": "broadcom-sta-dkms",
    "intel-legacy-accept-license": "firmware-ipw2x00",
}


def payload(action: str, directory: Path = DIRECTORY) -> Path | None:
    package = PACKAGES.get(action)
    if package is None:
        return None
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
        if manifest["format"] != 1:
            return None
        item = manifest["packages"][package]
        filename = item["filename"]
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".deb"):
            return None
        archive = directory / filename
        if archive.is_symlink() or not archive.is_file():
            return None
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        return archive if digest == item["sha256"] else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def license_text(action: str, directory: Path = DIRECTORY) -> str:
    package = PACKAGES.get(action)
    if package is None:
        return ""
    try:
        return (directory / "licenses" / (package + ".txt")).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def headers_available(kernel: str | None = None, modules: Path = Path("/lib/modules")) -> bool:
    return (modules / (kernel or os.uname().release) / "build/Makefile").is_file()


def selected(path: Path = CHOICES) -> list[str]:
    try:
        actions = json.loads(path.read_text())
        if isinstance(actions, list) and all(isinstance(action, str) and action in PACKAGES for action in actions):
            return list(dict.fromkeys(actions))
    except (OSError, ValueError, TypeError):
        pass
    return []


def remember(action: str, path: Path = CHOICES) -> None:
    if action not in PACKAGES:
        raise ValueError("Geçersiz sürücü seçimi")
    actions = list(dict.fromkeys([*selected(path), action]))
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(actions, stream)
        stream.write("\n")
    temporary.replace(path)
