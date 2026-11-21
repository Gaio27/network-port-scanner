import datetime as dt
import os
import socket
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import scanner as sc  # noqa: E402

FIXED_NOW = dt.datetime(2026, 11, 21, 9, 0, 0)


def test_expand_slash28_gives_14_hosts():
    hosts = sc.expand_targets("192.168.10.0/28")
    assert len(hosts) == 14
    assert hosts[0] == "192.168.10.1"
    assert hosts[-1] == "192.168.10.14"


def test_expand_slash31_and_32():
    assert sc.expand_targets("10.0.0.0/31") == ["10.0.0.0", "10.0.0.1"]
    assert sc.expand_targets("10.0.0.5/32") == ["10.0.0.5"]


def test_expand_single_ip():
    assert sc.expand_targets("10.1.1.1") == ["10.1.1.1"]


def test_expand_rejects_huge_block():
    with pytest.raises(ValueError):
        sc.expand_targets("10.0.0.0/8")


def test_expand_rejects_invalid_ip():
    with pytest.raises(ValueError):
        sc.expand_targets("999.1.1.1")


def test_scan_host_up_with_some_ports_open():
    open_set = {("10.0.0.1", 22), ("10.0.0.1", 443)}
    rows = sc.scan(
        ["10.0.0.1"],
        [22, 80, 443],
        pinger=lambda ip, t: True,
        checker=lambda ip, p, t: (ip, p) in open_set,
        now=FIXED_NOW,
    )
    assert [(r["port"], r["status_port"]) for r in rows] == [
        ("22", "open"),
        ("80", "closed"),
        ("443", "open"),
    ]
    assert all(r["status_host"] == "up" for r in rows)
    assert rows[0]["waktu"] == "2026-11-21T09:00:00"


def test_scan_host_down_writes_single_row_without_port():
    rows = sc.scan(
        ["10.0.0.9"],
        [22, 80],
        pinger=lambda ip, t: False,
        checker=lambda ip, p, t: False,
        now=FIXED_NOW,
    )
    assert rows == [
        {
            "waktu": "2026-11-21T09:00:00",
            "ip": "10.0.0.9",
            "status_host": "down",
            "port": "",
            "status_port": "",
        }
    ]


def test_scan_host_counts_as_up_if_port_open_even_when_ping_fails():
    rows = sc.scan(
        ["10.0.0.7"],
        [443],
        pinger=lambda ip, t: False,  # ICMP diblokir firewall
        checker=lambda ip, p, t: True,
        now=FIXED_NOW,
    )
    assert rows[0]["status_host"] == "up"
    assert rows[0]["status_port"] == "open"


def test_scan_handles_multiple_hosts_in_parallel():
    targets = [f"10.0.0.{i}" for i in range(1, 21)]
    rows = sc.scan(
        targets,
        [22],
        workers=8,
        pinger=lambda ip, t: ip.endswith("0"),
        checker=lambda ip, p, t: False,
        now=FIXED_NOW,
    )
    assert len(rows) == 20
    up = {r["ip"] for r in rows if r["status_host"] == "up"}
    assert up == {f"10.0.0.{i}" for i in (10, 20)}


def test_write_csv(tmp_path):
    out = tmp_path / "hasil.csv"
    rows = [sc._row("2026-11-21T09:00:00", "10.0.0.1", "up", "22", "open")]
    sc.write_csv(rows, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "waktu,ip,status_host,port,status_port"
    assert lines[1] == "2026-11-21T09:00:00,10.0.0.1,up,22,open"


def test_check_port_detects_listening_socket():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        assert sc.check_port("127.0.0.1", port, timeout=1.0) is True
    finally:
        server.close()


def test_check_port_detects_closed_port():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # port dilepas, sekarang seharusnya tertutup
    assert sc.check_port("127.0.0.1", port, timeout=0.5) is False
