# Comparație metode de rating foto: NIMA (AI) vs euristică

**Studiu de performanță și acord între cele două metode de evaluare automată a
calității pozelor, măsurat pe dispozitivul real (Raspberry Pi 4).**

Date colectate: 2026-06-16. Eșantion: **100 de poze reale** (Sony A7, JPEG ~24 MP),
selectate aleator (seed fix) dintr-o sesiune de backup de 6566 de fișiere.

---

## 1. Cele două metode comparate

| | **NIMA** (model AI) | **Euristică** (reguli) |
|---|---|---|
| Tip | Rețea neuronală (MobileNet) antrenată pe setul **AVA** | Formule pe baza histogramei și a gradientului |
| Ce măsoară | **Calitate estetică** (compoziție, atractivitate — „învățată" din ~250k poze notate de oameni) | **Calitate tehnică**: claritate (varianța Laplacianului), expunere (clipping), contrast |
| Ieșire | Distribuție peste scoruri 1–10 → media → 1–5 stele | Scor 1–5 din combinație ponderată |
| Rulare | ONNX Runtime pe CPU | NumPy |
| Dependențe | model `nima.onnx` (~13 MB) + onnxruntime | doar NumPy |

Ambele scriu același rezultat (1–5 stele) în metadata pozei (`XMP:Rating`) și în
manifestul sesiunii. Euristica e folosită automat ca **fallback** când modelul AI
lipsește.

---

## 2. Metodologie

- **Hardware:** Raspberry Pi 4 Model B (4 GB RAM, CPU Cortex-A72 4×1.5 GHz), poze
  citite de pe SSD-ul SanDisk Extreme 1 TB.
- **Procedură:** pentru fiecare poză se face o singură **decodare** (comună), apoi se
  calculează în paralel scorul NIMA și scorul euristic, cronometrând fiecare etapă.
- **Reproductibil:** `scripts/benchmark_rating.py` (rezultate brute în
  `/mnt/backup-ssd/logs/benchmark_rating.csv`). Benchmark-ul **nu modifică** pozele.

---

## 3. Rezultate — viteză

Timpi medii pe poză (ms), pe Raspberry Pi 4:

| Etapă | Timp / poză |
|---|---|
| Decodare JPEG ~24 MP (comună ambelor) | **1505.8 ms** |
| Inferență NIMA (ONNX, CPU) | **1198.2 ms** |
| Calcul euristic (NumPy) | **395.3 ms** |
| **TOTAL NIMA** (decodare + inferență) | **2704.0 ms** (≈ 2.7 s) |
| **TOTAL euristică** (decodare + calcul) | **1901.0 ms** (≈ 1.9 s) |

| Throughput | Poze / minut |
|---|---|
| NIMA | **22.2** |
| Euristică | **31.6** |

**Observații:**
- Euristica este cu **~42 % mai rapidă** decât NIMA (1.9 s vs 2.7 s per poză).
  Diferența vine din inferența rețelei neuronale (~1.2 s) față de calculul NumPy (~0.4 s).
- **Decodarea imaginii domină** costul (1.5 s, ~56 % din timpul NIMA și ~79 % din cel
  euristic). O optimizare a decodării (rezoluție redusă) ar accelera ambele metode.
- Extrapolare pentru o sesiune mare: ~1000 de poze ≈ **45 min cu NIMA** vs **32 min
  cu euristica**.

---

## 4. Rezultate — distribuția stelelor (100 poze)

| Stele | 1★ | 2★ | 3★ | 4★ | 5★ | Medie |
|---|---|---|---|---|---|---|
| **NIMA** | 9 | 55 | 25 | 10 | 1 | 4.61 / 10 |
| **Euristică** | 3 | 27 | 55 | 14 | 1 | 2.79 / 5 |

NIMA este mai „sever" (concentrează pozele la **2★**), iar euristica este mai
„indulgentă" (concentrează la **3★**). Pentru aceste instantanee obișnuite, ambele
acordă rar 5★ (1 poză fiecare).

---

## 5. Rezultate — gradul de acord între metode

| Metric | Valoare |
|---|---|
| Stele identice | **33.0 %** |
| În interval de ±1 stea | **83.0 %** |
| Diferență medie (stele) | 0.86 |
| **Corelație scoruri brute** | **0.041** |
| Corelație stele | 0.093 |

### Concluzia cheie a comparației
Corelația de **~0.04** (practic **zero**) arată că **cele două metode măsoară lucruri
fundamental diferite**: euristica evaluează *calitatea tehnică* (o poză clară și bine
expusă), în timp ce NIMA evaluează *calitatea estetică* (o poză „plăcută", învățată din
preferințe umane). O poză poate fi tehnic perfectă, dar estetic banală — și invers.

Cele două metode sunt deci **complementare, nu redundante**.

---

## 6. Exemple ilustrative

**Poze apreciate estetic de NIMA (dar doar medii tehnic):**
| Fișier | NIMA | Euristică |
|---|---|---|
| A7409563.JPG | 5.80 (5★) | 2.92 (3★) |
| A7400373.JPG | 5.58 (4★) | 2.72 (3★) |

**Poze slabe după ambele metode (acord):**
| Fișier | NIMA | Euristică |
|---|---|---|
| A7406213.JPG | 3.62 (1★) | 1.41 (1★) |
| A7407386.JPG | 3.66 (1★) | 1.26 (1★) |

**Dezacordul maxim — exemplul reprezentativ pentru diferența dintre metode:**
| Fișier | NIMA | Euristică | Interpretare |
|---|---|---|---|
| **A7409811.JPG** | **1★** | **5★** | Tehnic impecabilă (clară, bine expusă) → euristica o adoră; estetic banală → NIMA o respinge. |

---

## 7. Cum se reproduce comparația

Pe Raspberry Pi (cu modelul `models/nima.onnx` prezent):
```bash
cd /home/admin/photobackup
./venv/bin/python scripts/benchmark_rating.py <session_id> 100
# rezultat brut: /mnt/backup-ssd/logs/benchmark_rating.csv
```

Generarea modelului NIMA (pe o mașină de dezvoltare): vezi
[`scripts/convert_nima_to_onnx.py`](scripts/convert_nima_to_onnx.py) și
[`models/README.md`](models/README.md).

---

## 8. Concluzie

| | NIMA (AI) | Euristică |
|---|---|---|
| Viteză (Pi 4) | 2.7 s / poză (22 poze/min) | 1.9 s / poză (32 poze/min) |
| Ce oferă | curare „ca a unui om" (estetică) | filtru tehnic rapid |
| Cost | model 13 MB + inferență CPU | aproape gratuit |

Euristica este un **filtru tehnic rapid și gratuit**, ideal ca fallback și pentru
trierea rapidă a pozelor evident proaste (neclare/supra/subexpuse). NIMA adaugă o
**dimensiune estetică învățată**, mai apropiată de judecata umană, cu un cost de viteză
moderat (~42 %). Corelația aproape nulă dintre ele confirmă că aduc informație
**complementară** — un sistem ideal le-ar putea combina (ex. euristica elimină întâi
pozele defecte, apoi NIMA ordonează estetic restul).
