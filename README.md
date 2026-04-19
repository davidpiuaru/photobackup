# PhotoBackup — dispozitiv portabil de backup automat

Proiect de licență. Dispozitiv headless bazat pe Raspberry Pi 4 care, la introducerea unui SD card într-un USB card reader, copiază automat fișierele pe un SSD extern și le sincronizează pe Google Drive când are conexiune la internet.

## Hardware

- Raspberry Pi 4 (Raspberry Pi OS Lite 64-bit, hostname `photobackup`)
- SSD extern USB (SanDisk Extreme 1TB) → `/mnt/backup-ssd` (ext4, label `BACKUP_SSD`)
- USB SD Card Reader (Genesys Logic, vendor 05e3:0764) — slot SD + microSD
- LED-uri pe GPIO (opțional): verde feedback OK, roșu feedback eroare

## Structură pe SSD

```
/mnt/backup-ssd/
├── backups/          # foldere YYYY-MM-DD_HH-MM-SS/ cu fișierele copiate + manifest.json
├── logs/             # photobackup.log (rotating)
└── sync_queue/       # global_manifest.json (deduplicare) + sync_state.json
```

## Module

| Fișier | Rol |
|---|---|
| `photobackup/main.py` | Entry point — logging, LED idle, pornire monitor |
| `photobackup/monitor.py` | Observer pyudev pentru evenimente `add` partiție SD |
| `photobackup/mounter.py` | Mount/umount SD card prin `udisksctl` |
| `photobackup/copier.py` | rsync + verificare SHA256 + marker `.incomplete` |
| `photobackup/tracker.py` | Manifest global pentru deduplicare |
| `photobackup/led.py` | Wrapper gpiozero (no-op dacă lipsește hardware) |
| `photobackup/config.py` | Path-uri, ID-uri USB, pin-uri GPIO |
| `photobackup/sync.py` | Sincronizare Google Drive (rclone), rulat de timer systemd |

## Servicii systemd

- `photobackup.service` — daemon principal (urmărește SD card events)
- `photobackup-sync.timer` — sincronizare Google Drive la fiecare 10 minute

## Instalare

Vezi planul detaliat în `docs/SETUP.md` (sau planul de execuție pas-cu-pas folosit la dezvoltare).
