"""Antarmuka baris perintah untuk pemindai host dan port."""

from __future__ import annotations

import argparse
import sys

import scanner as sc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pemindai host dan port TCP sederhana")
    p.add_argument("target", help="CIDR atau satu IP, contoh: 192.168.10.0/28")
    p.add_argument("--ports", type=int, nargs="+", default=sc.DEFAULT_PORTS, help="daftar port TCP")
    p.add_argument("--workers", type=int, default=50, help="jumlah pemindaian paralel")
    p.add_argument("--timeout", type=float, default=1.0, help="batas waktu per percobaan, dalam detik")
    p.add_argument("--out", required=True, help="file CSV hasil")
    args = p.parse_args(argv)

    try:
        targets = sc.expand_targets(args.target)
        rows = sc.scan(targets, args.ports, workers=args.workers, timeout=args.timeout)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    sc.write_csv(rows, args.out)
    hosts_up = len({r["ip"] for r in rows if r["status_host"] == "up"})
    open_count = sum(1 for r in rows if r["status_port"] == "open")
    print(f"Host dipindai: {len(targets)}, aktif: {hosts_up}, port terbuka: {open_count}")
    print(f"Hasil disimpan di {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
