#!/usr/bin/env python3
"""Bir CI komutunu çalıştırır; hata kuyruğunu GitHub kontrol notuna da yazar.

Standart çıktı anlık olarak korunur. Böylece günlük arşivine erişilemediğinde
bile asıl hata, Actions kontrolünün annotations API'sinden incelenebilir.
"""
from __future__ import annotations

import argparse
import collections
import subprocess
import sys


def escape_data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def emit_error(title: str, text: str) -> None:
    title = escape_data(title).replace(":", "%3A").replace(",", "%2C")
    # Actions annotations API iletiyi 4096 karakterde kesebiliyor. Büyük bir
    # ilerleme çıktısının BAŞINI değil gerçek hatanın bulunduğu SONUNU sakla.
    print(f"::error title={title}::{escape_data(text[-3500:])}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="OğuzDows CI")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("Çalıştırılacak komutu -- sonrasında belirtin.")
    tail: collections.deque[str] = collections.deque(maxlen=80)
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace", bufsize=1) as process:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                tail.append(line)
            returncode = process.wait()
    except OSError as error:
        emit_error(args.title, str(error))
        return 127
    if returncode:
        emit_error(args.title, "".join(tail) or f"Komut çıkış kodu: {returncode}")
    return returncode if returncode >= 0 else 128 - returncode


if __name__ == "__main__":
    raise SystemExit(main())
