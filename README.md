# PhotoBackup — dispozitiv portabil de backup automat

Proiect de licență. Dispozitiv headless bazat pe Raspberry Pi 4 care, la
introducerea unui SD card într-un USB card reader, copiază automat fișierele pe
un SSD extern și le sincronizează pe Google Drive când are conexiune la
internet. Fără ecran, fără tastatură — plug & play.

## Flux de operare

```
 ┌──────────────┐    plug SD    ┌──────────────┐   copy   ┌──────────────┐
 │   camera     │ ────────────► │  card reader │ ───────► │  SSD (ext4)  │
 │  SD card     │    (USB)      │  (USB)       │  rsync-  │ /mnt/backup- │
 └──────────────┘               └──────────────┘  like    │   ssd/       │
                                                          └──────┬───────┘
                                                                 │ rclone
                                                                 ▼
                                                          ┌──────────────┐
                                                          │ Google Drive │
                                                          │ PhotoBackup/ │
                                                          └──────────────┘
```

La fiecare inserție: daemon-ul detectează evenimentul prin `pyudev`, filtrează
după vendor/model USB ca să nu confunde cardul reader cu SSD-ul, montează
partiția `read-only` sub `/media/photobackup/<label>`, copiază fișierele noi
(filtrate prin manifest global de deduplicare), calculează SHA256 pe fiecare
fișier copiat comparând cu sursa, scrie un manifest JSON al backup-ului, și
demontează cardul. Un timer systemd separat sincronizează periodic (10 min)
backup-urile complete pe Google Drive via `rclone`, sărind folderele marcate
`.incomplete`.

## Hardware

- Raspberry Pi 4 (Raspberry Pi OS Lite 64-bit, hostname `photobackup`)
- SSD extern USB 3.0 (SanDisk Extreme 1TB) montat la `/mnt/backup-ssd`
  (ext4, label `BACKUP_SSD`)
- USB SD Card Reader (Genesys Logic, `05e3:0764`) — identificat prin
  `ID_VENDOR_ID` + `ID_MODEL_ID` în udev
- LED-uri pe GPIO (opțional, încă neimplementat fizic):
  - GPIO 17 = verde (idle fix / working blink)
  - GPIO 27 = roșu (eroare)

## Structură pe SSD

```
/mnt/backup-ssd/
├── backups/
│   └── YYYY-MM-DD_HH-MM-SS_<label>/
│       ├── <files copied from SD card, preserving subfolder structure>
│       └── manifest.json           # listă fișiere + SHA256
├── logs/
│   ├── photobackup.log             # daemon principal (rotating 5×5MB)
│   └── sync.log                    # sincronizare Google Drive
└── sync_queue/
    ├── global_manifest.json        # deduplicare cross-sesiuni
    └── sync_state.json             # backup-uri deja urcate pe Drive
```

## Module Python (`photobackup/`)

| Fișier | Rol |
|---|---|
| `main.py` | Entry point — logging rotating, LED idle, pornire monitor |
| `monitor.py` | `pyudev.MonitorObserver` — filtrează după vendor/model USB |
| `mounter.py` | `mount`/`umount` prin sudo (NOPASSWD) la `/media/photobackup/<label>` |
| `copier.py` | Copiere + verificare SHA256 + `.incomplete` marker + manifest JSON |
| `tracker.py` | Manifest global pentru deduplicare între inserții |
| `sync.py` | Upload periodic pe Google Drive via `rclone` |
| `led.py` | Wrapper `gpiozero` — no-op dacă hardware-ul lipsește |
| `config.py` | Path-uri, ID-uri USB, pin-uri GPIO, remote rclone |

## Servicii systemd

Fișiere în `systemd/`:

- `photobackup.service` — daemon principal, pornit la `multi-user.target`,
  `Restart=on-failure` după 5s
- `photobackup-sync.service` + `.timer` — `oneshot` la fiecare 10 min
  (`OnBootSec=2min`, `OnUnitActiveSec=10min`, `Persistent=true`)
- `photobackup-api.service` — FastAPI (uvicorn) pe `:8080` pentru app-ul iOS
- `photobackup-wifi.service` — wifi_manager.py (AP ↔ Client)
- `avahi-photobackup.service` — se copiază la `/etc/avahi/services/photobackup.service`
  pentru descoperire Bonjour (`_photobackup._tcp`)

## App iOS companion

Proiectul SwiftUI e în [ios/](ios/). Se generează `.xcodeproj` cu
[XcodeGen](https://github.com/yonaskolb/XcodeGen):

```bash
brew install xcodegen
cd ios/
xcodegen generate
open PhotoBackup.xcodeproj
```

Aplicația detectează automat Pi-ul pe rețea (Bonjour) sau în mod hotspot
(`10.42.0.1`) și expune 5 tab-uri: Dashboard, Backup, Galerie, Wi-Fi, Setări.
Vezi [ios/README.md](ios/README.md) pentru detalii.

## Wi-Fi Manager (AP ↔ Client automat)

`photobackup/wifi_manager.py` rulează ca serviciu systemd (root). Logică:

1. La pornire încearcă conexiunile Wi-Fi salvate; dacă niciuna nu e disponibilă
   în 30s → pornește hotspot-ul `PhotoBackup-AP` (parola implicită
   `photobackup123`, IP `10.42.0.1`).
2. În mod client: dacă pierde conexiunea >60s → revine automat la AP.
3. În mod AP: primește comenzi din `/tmp/photobackup-wifi.cmd` (scris de API)
   pentru a comuta la o rețea nouă aleasă din app-ul iOS.

Stare curentă în `/tmp/wifi_state.json` (citită de API).

## Robustețe

- **Deduplicare**: manifest global `(path, size, mtime) → sha256`. Dacă
  reintroduci același card, se loghează "0 fișiere noi" și folderul de backup
  gol este șters.
- **Scoatere prematură a cardului**: `.incomplete` marker rămâne în folder,
  iar sync-ul pe Drive sare peste el. Un retry ulterior va copia doar
  fișierele lipsă.
- **Pi pornește fără SSD**: `nofail` în `/etc/fstab` — sistemul bootează
  oricum; daemon-ul scrie loguri doar dacă mount point-ul există.
- **Identificare hardware strictă**: prin vendor + model USB, nu după
  litera de device (care poate varia la reboot).
- **Mount read-only**: cardul SD nu e modificat niciodată — rollback
  natural.
- **Verificare integritate**: SHA256 calculat pe destinație este comparat
  cu SHA256-ul sursei pentru fiecare fișier. Mismatch → `.incomplete` +
  log de eroare.
- **Scope OAuth minim**: `drive.file` — rclone vede doar fișierele create
  de acest app; dacă Pi-ul e compromis, restul Drive-ului rămâne protejat.

## Instalare pe Pi

Rezumat — pași detaliați mai jos:

1. Raspberry Pi OS Lite 64-bit, SSH activat, Wi-Fi configurat prin Pi Imager
2. `sudo apt install python3-pyudev udisks2 exfat-fuse exfatprogs rsync rclone git avahi-daemon network-manager`
3. Formatează SSD-ul ext4 (`mkfs.ext4 -L BACKUP_SSD`), adaugă în `/etc/fstab`
   cu UUID și `nofail,noatime`
4. `git clone` acest repo în `/home/admin/photobackup/`
5. Creează venv: `python3 -m venv --system-site-packages venv`, apoi
   `./venv/bin/pip install -r requirements.txt`
6. Configurează rclone pentru Google Drive cu scope `drive.file`:
   - Pe o mașină cu browser: `rclone authorize "drive" "$(echo -n '{"scope":"drive.file"}' | base64 | tr -d '=' | tr '+/' '-_')"`
   - Copiază token-ul în `~/.config/rclone/rclone.conf` pe Pi
7. Instalează serviciile:
   ```
   sudo cp systemd/photobackup.service \
           systemd/photobackup-sync.service systemd/photobackup-sync.timer \
           systemd/photobackup-api.service systemd/photobackup-wifi.service \
           /etc/systemd/system/
   sudo cp systemd/avahi-photobackup.service /etc/avahi/services/photobackup.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now photobackup.service photobackup-sync.timer \
                               photobackup-api.service photobackup-wifi.service
   sudo systemctl restart avahi-daemon
   ```

## Verificare

- `systemctl status photobackup` → `active (running)`
- `systemctl list-timers photobackup-sync.timer` → programare vizibilă
- Inserează un SD card → urmărește `journalctl -u photobackup -f`
- `ls /mnt/backup-ssd/backups/` → vezi folderul de backup cu timestamp
- `rclone lsf gdrive:PhotoBackup/` → fișierele urcate pe Drive

## Troubleshooting

| Simptom | Cauză probabilă | Fix |
|---|---|---|
| Daemon nu pornește | venv lipsă sau `pyudev` not found | `python3 -m venv --system-site-packages venv` |
| "Not authorized" la mount | polkit blochează `udisksctl` headless | Folosim `sudo mount` direct (cu NOPASSWD) |
| Card detectat dar nu se montează | fs-ul nu e suportat | `sudo apt install exfat-fuse ntfs-3g` |
| Sync Drive loop-uie pe eroare | expirare refresh_token | Reauthorizează cu `rclone authorize` |
| `journalctl` gol după inserție | vendor/model USB nu se potrivește | `udevadm info -q property -n /dev/sdX` pentru debug |

## Licență

Proiect academic — cod open-source (MIT).
