#!/usr/bin/python3 -I
"""Canlı kurucu için gerçek squashfs yolunu ve onaylanmış sürücüleri hazırlar."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, "/usr/lib/oguzdows")
from offline import selected

MEDIA = (Path("/run/live/medium"), Path("/lib/live/mount/medium"), Path("/run/live/findiso"))
ACTIONS = ("broadcom", "intel-legacy-accept-license")


def source(media=MEDIA) -> Path:
    for base in media:
        squashfs = base / "live/filesystem.squashfs"
        if squashfs.is_file():
            return squashfs
    raise FileNotFoundError("OğuzDows kurulum kaynağı bulunamadı. Canlı USB'nin bağlı olduğundan emin ol.")


def prepare(directory: Path = Path("/etc/calamares"), media=MEDIA, actions=None) -> None:
    if not (directory / "settings.conf").is_file():
        raise FileNotFoundError("OğuzDows kurucu ayarları bulunamadı.")
    unpack = {"unpack": [{"source": str(source(media)), "sourcefs": "squashfs", "destination": ""}]}
    drivers = {"actions": list(dict.fromkeys(action for action in (selected() if actions is None else actions)
                                             if isinstance(action, str) and action in ACTIONS))}
    for name, data in (("unpackfs", unpack), ("selected-drivers", drivers)):
        (directory / "modules" / (name + ".conf")).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


if __name__ == "__main__":
    prepare()
