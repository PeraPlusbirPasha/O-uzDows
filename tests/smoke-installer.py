#!/usr/bin/env python3
"""Gerçek Calamares'i Xvfb'de açar. Hiçbir kurulum düğmesine basmaz."""
import argparse
import os
import subprocess
import tempfile
import time
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("test-results"))
    args = parser.parse_args()
    if args.config.resolve() != Path("/etc/calamares") or not (args.config / "settings.conf").is_file():
        raise RuntimeError("Bu kontrol standart /etc/calamares/settings.conf ayarlarını kullanır.")
    args.output.mkdir(parents=True, exist_ok=True)
    logpath = args.output / "installer.log"
    with tempfile.TemporaryDirectory(prefix="oguzdows-installer-smoke-") as home, logpath.open("w") as log:
        env = {**os.environ, "HOME": home, "QT_QPA_PLATFORMTHEME": "gtk3", "QT_QUICK_BACKEND": "software", "LIBGL_ALWAYS_SOFTWARE": "1"}
        # Aynı normal arama yolu üretimdeki başlatıcıda da kullanılır.
        process = subprocess.Popen(["/usr/bin/calamares", "-D", "8"], stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            deadline = time.monotonic() + 55
            while time.monotonic() < deadline:
                text = logpath.read_text(errors="replace")
                if "STARTUP: failed modules are" in text or "Cowardly refusing to continue startup" in text:
                    raise RuntimeError("Kurucu modülleri / markalaması yüklenemedi:\n" + text[-14000:])
                if process.poll() is not None:
                    raise RuntimeError(f"Kurucu erken kapandı ({process.returncode}):\n" + text[-14000:])
                if "Window now visible and ProgressTreeView populated" in text:
                    # Yalnızca pencereyi göster; klavye/fare olayı ve disk yazımı yok.
                    time.sleep(.5)
                    root = Gdk.get_default_root_window()
                    pixbuf = Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height())
                    if pixbuf is None:
                        raise RuntimeError("Kurucu ekran görüntüsü alınamadı.")
                    pixbuf.savev(str(args.output / "installer.png"), "png", [], [])
                    print("Gerçek OğuzDows kurucusu ve modülleri açıldı; disk kurulumu yapılmadı.")
                    return
                time.sleep(.2)
            raise RuntimeError("Kurucu açılışı zaman aşımı:\n" + logpath.read_text(errors="replace")[-14000:])
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
