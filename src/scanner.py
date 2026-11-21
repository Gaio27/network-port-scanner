"""Pemindai host dan port TCP untuk lab dan pemeriksaan jaringan sendiri.

Gunakan hanya pada jaringan yang Anda miliki atau yang secara tertulis diizinkan untuk diuji.
"""

from __future__ import annotations

import csv
import datetime as dt
import ipaddress
import os
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Iterable

DEFAULT_PORTS = [22, 80, 443]
MAX_TARGETS = 4096  # batas pengaman agar tidak memindai blok yang terlalu besar tanpa sengaja

CSV_HEADER = ["waktu", "ip", "status_host", "port", "status_port"]


def expand_targets(target: str) -> list[str]:
    """Mengubah CIDR (atau satu IP) menjadi daftar alamat host yang akan dipindai."""
    if "/" not in target:
        ipaddress.IPv4Address(target)  # validasi
        return [target]
    net = ipaddress.IPv4Network(target, strict=False)
    if net.num_addresses > MAX_TARGETS:
        raise ValueError(f"Blok {target} berisi {net.num_addresses} alamat, batasnya {MAX_TARGETS}")
    if net.prefixlen >= 31:
        hosts = list(net)  # /31 dan /32 tidak punya alamat jaringan atau broadcast untuk host
    else:
        hosts = list(net.hosts())
    return [str(h) for h in hosts]


def ping_host(ip: str, timeout: float = 1.0) -> bool:
    """Mengirim satu ICMP echo. Mengembalikan False jika perintah ping tidak tersedia."""
    if os.name == "nt":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(round(timeout)))), ip]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def check_port(ip: str, port: int, timeout: float = 1.0) -> bool:
    """Mencoba koneksi TCP. True jika port menerima koneksi."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def scan(
    targets: Iterable[str],
    ports: list[int],
    workers: int = 50,
    timeout: float = 1.0,
    pinger: Callable[[str, float], bool] = ping_host,
    checker: Callable[[str, int, float], bool] = check_port,
    now: dt.datetime | None = None,
) -> list[dict[str, str]]:
    """Memindai setiap host dan port, lalu mengembalikan baris hasil siap ditulis ke CSV.

    Host dianggap aktif jika ping berhasil atau salah satu port yang diperiksa terbuka.
    Host yang tidak aktif tetap dicatat dengan satu baris tanpa port.
    """
    stamp = (now or dt.datetime.now()).isoformat(timespec="seconds")
    targets = list(targets)

    def probe(ip: str) -> list[dict[str, str]]:
        pinged = pinger(ip, timeout)
        open_ports = [p for p in ports if checker(ip, p, timeout)]
        is_up = pinged or bool(open_ports)
        status_host = "up" if is_up else "down"
        if not ports or not open_ports:
            # Tidak ada port terbuka: tulis satu baris untuk host, tanpa detail port
            if not is_up:
                return [_row(stamp, ip, status_host, "", "")]
        rows = []
        for p in ports:
            rows.append(_row(stamp, ip, status_host, str(p), "open" if p in open_ports else "closed"))
        return rows

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(probe, targets))
    return [row for group in results for row in group]


def _row(stamp: str, ip: str, status_host: str, port: str, status_port: str) -> dict[str, str]:
    return {
        "waktu": stamp,
        "ip": ip,
        "status_host": status_host,
        "port": port,
        "status_port": status_port,
    }


def write_csv(rows: list[dict[str, str]], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)
