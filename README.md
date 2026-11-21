# Network Port dan Host Scanner

Alat ringan untuk memeriksa host yang aktif dan port TCP yang terbuka di satu segmen jaringan, dengan hasil disimpan ke CSV. Dibuat untuk lab sendiri dan untuk belajar pemeriksaan jaringan yang terdokumentasi.

> **Penting:** gunakan alat ini hanya pada jaringan dan perangkat yang Anda miliki atau yang secara tertulis diizinkan untuk diuji.

## Masalah

Tim jaringan sering perlu tahu host mana yang hidup dan port mana yang terbuka di satu VLAN, misalnya setelah perubahan firewall. Memeriksanya satu per satu lambat dan tidak terdokumentasi.

## Pendekatan

- Python dengan `subprocess` untuk ping dan `socket` untuk pemeriksaan port TCP.
- `concurrent.futures.ThreadPoolExecutor` agar pemeriksaan paralel tetap cepat.
- Keluaran CSV dengan waktu pemeriksaan, sehingga hasil bisa dibandingkan dari waktu ke waktu.

## Fitur

- Ping dan pemeriksaan port paralel ke rentang CIDR atau satu IP. Batas aman 4096 alamat per pemindaian.
- Host dianggap aktif jika ping berhasil atau salah satu port terbuka, sehingga host yang memblokir ICMP tetap terdeteksi.
- Pemeriksaan port TCP umum (22, 23, 80, 443, 3389, dan port yang Anda tentukan).
- Batas waktu dan jumlah pekerja (worker) bisa diatur.
- Keluaran CSV: `waktu, ip, status_host, port, status_port`.

## Arsitektur

```
src/
  scanner.py      # expand_targets, ping_host, check_port, scan, write_csv
  cli.py          # argparse
tests/
  test_scanner.py # pengujian dengan fungsi ping dan port palsu, plus uji loopback
```

## Cara menjalankan

```bash
git clone https://github.com/Gaio27/network-port-scanner.git
cd network-port-scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Ping dan port 22, 80, 443 untuk satu subnet lab
python3 src/cli.py 192.168.10.0/28 --ports 22 80 443 --out hasil.csv

# Hanya satu alamat
python3 src/cli.py 127.0.0.1/32 --ports 22 --out hasil.csv

# Pengujian
pytest -v
```

## Contoh keluaran CSV

```
waktu,ip,status_host,port,status_port
2026-11-21T09:00:00,192.168.10.1,up,22,open
2026-11-21T09:00:00,192.168.10.1,up,80,closed
2026-11-21T09:00:00,192.168.10.2,down,,
```

## Hasil

- [x] `pytest`: 12 pengujian lulus (termasuk uji port TCP nyata di loopback)
- [ ] Jumlah host yang diuji di jaringan lab: (isi setelah pengujian di lab)

## Yang saya pelajari dan akan saya perbaiki

- Tantangan utama adalah timeout: host yang tidak merespons memperlambat seluruh pemindaian jika batas waktu terlalu besar.
- Rencana berikutnya: menambahkan ARP scan untuk segmen lokal dan membandingkan hasil dengan keluaran sebelumnya.

## Lisensi

MIT
