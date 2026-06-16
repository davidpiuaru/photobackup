"""Benchmark comparativ NIMA vs euristică pe N poze: viteză + grad de acord.

Rulare pe Pi (cu modelul NIMA prezent la models/nima.onnx):
    ./venv/bin/python scripts/benchmark_rating.py <session_id> [N]

Nu modifică pozele (doar citește + calculează scoruri). Scrie un CSV per-poză în
/mnt/backup-ssd/logs/benchmark_rating.csv și afișează un sumar JSON.
"""
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
from photobackup import config, imaging, scoring


def _clamp_stars(x: float) -> int:
    return int(round(min(5.0, max(1.0, x))))


def main() -> None:
    session = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    root = config.BACKUPS_DIR / session
    imgs = [p for p in root.rglob("*") if p.suffix.lower() in config.IMAGE_EXT]
    random.seed(42)
    random.shuffle(imgs)
    imgs = imgs[:n]

    nima = scoring.Scorer()
    if nima.method != "nima":
        sys.exit("EROARE: modelul NIMA nu e incarcat (scorer pe euristica)")

    rows, td, tn, th = [], 0.0, 0.0, 0.0
    for p in imgs:
        t = time.monotonic(); img = imaging.load_image(p); td += time.monotonic() - t
        t = time.monotonic(); mean_n = nima._nima_mean(img); tn += time.monotonic() - t
        stars_n = scoring.stars_from_mean(mean_n)
        t = time.monotonic(); h = scoring.heuristic_score(img); th += time.monotonic() - t
        rows.append((p.name, round(mean_n, 3), stars_n, round(h, 3), _clamp_stars(h)))

    k = len(rows)
    nm = np.array([r[1] for r in rows]); hs = np.array([r[3] for r in rows])
    sn = np.array([r[2] for r in rows]); sh = np.array([r[4] for r in rows])

    csv = config.SSD_MOUNT / "logs" / "benchmark_rating.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    with csv.open("w") as f:
        f.write("file,nima_mean,nima_stars,heur_score,heur_stars\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")

    print(json.dumps({
        "n": k,
        "timp_ms_per_poza": {
            "decode (comun)": round(td / k * 1000, 1),
            "inferenta NIMA": round(tn / k * 1000, 1),
            "calcul euristic": round(th / k * 1000, 1),
            "TOTAL NIMA (decode+inferenta)": round((td + tn) / k * 1000, 1),
            "TOTAL euristic (decode+calcul)": round((td + th) / k * 1000, 1),
        },
        "throughput_poze_pe_minut": {
            "NIMA": round(k / (td + tn) * 60, 1),
            "euristic": round(k / (td + th) * 60, 1),
        },
        "distributie_stele": {
            "NIMA": {str(s): int((sn == s).sum()) for s in range(1, 6)},
            "euristic": {str(s): int((sh == s).sum()) for s in range(1, 6)},
        },
        "acord_intre_metode": {
            "stele_identice_%": round(float((sn == sh).mean() * 100), 1),
            "in_+-1_stea_%": round(float((np.abs(sn - sh) <= 1).mean() * 100), 1),
            "diferenta_medie_stele": round(float(np.abs(sn - sh).mean()), 2),
            "corelatie_scoruri_brute": round(float(np.corrcoef(nm, hs)[0, 1]), 3),
            "corelatie_stele": round(float(np.corrcoef(sn, sh)[0, 1]), 3),
        },
        "csv": str(csv),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
