#!/usr/bin/env python3
"""Pi için sınırlandırılmış zram ve VM politikası. CPU voltajına/saatine dokunmaz."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pi_support import current_policy, is_pi


def write_changed(path: Path, content: str, mode: int = 0o644) -> None:
    if path.is_file() and path.read_text() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(content)
    temporary.chmod(mode)
    temporary.replace(path)


def apply(root: Path = Path("/")) -> dict:
    if not is_pi(root):
        raise ValueError("Bu ayarlar yalnızca Raspberry Pi imajında uygulanır.")
    settings = current_policy(root)
    write_changed(root / "etc/default/zramswap",
                  "# OğuzDows Pi: /etc/oguzdows/pi.conf dosyasından üretilir.\n"
                  f"ALGO=lz4\nSIZE={settings['zram_mb']}\nPRIORITY=100\n")
    for name, value in (("swappiness", settings["swappiness"]), ("page-cluster", settings["page_cluster"])):
        target = root / "proc/sys/vm" / name
        if target.exists():
            target.write_text(str(value) + "\n")
    write_changed(root / "run/oguzdows/pi-profile.json", json.dumps(settings, indent=2) + "\n")
    return settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Root ile uygula; varsayılan yalnızca gösterir")
    args = parser.parse_args()
    if args.apply and os.geteuid() != 0:
        parser.error("Uygulamak için yönetici yetkisi gerekli.")
    settings = apply() if args.apply else current_policy()
    print(json.dumps(settings, ensure_ascii=False))


if __name__ == "__main__":
    main()
