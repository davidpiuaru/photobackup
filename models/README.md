# Model NIMA (scor estetic AI)

Pune aici modelul **NIMA** (Neural Image Assessment) în format **ONNX**, ca
fișierul:

```
models/nima.onnx
```

Calea e configurată în [`photobackup/config.py`](../photobackup/config.py)
(`NIMA_MODEL`). Dacă fișierul **lipsește** sau `onnxruntime` nu e instalat,
scorer-ul cade automat pe **euristică** (claritate/expunere/contrast) — deci
funcționalitatea merge și fără model, doar mai puțin „inteligent".

## Cerințe model
- Backbone tipic: MobileNet (NIMA aesthetic), antrenat pe AVA.
- **Input:** imagine 224×224 RGB. Scorer-ul detectează automat layout-ul
  (NCHW `1×3×224×224` sau NHWC `1×224×224×3`) din metadatele ONNX și aplică
  normalizare ImageNet.
- **Output:** vector de **10** valori (distribuție peste scorurile 1–10).
  Scorer-ul calculează media ponderată → 1–10, apoi o mapează la 1–5 stele prin
  `config.RATING_THRESHOLDS`.

## Cum obții modelul
- Conversie din proiectul *idealo/image-quality-assessment* (Keras → ONNX), sau
- Un model NIMA aesthetic ONNX pre-convertit (ex. de pe Hugging Face).

Apoi, pe Pi:
```bash
NIMA_URL="https://.../nima.onnx" ./scripts/get_nima_model.sh
sudo systemctl restart photobackup-api   # (rater-ul îl încarcă la fiecare rulare)
```

## Calibrare
După ce pui modelul, evaluează câteva sesiuni și, dacă distribuția stelelor e
prea „blândă"/„aspră", ajustează pragurile din `config.RATING_THRESHOLDS`
(implicit `[4.0, 4.75, 5.25, 5.75]`).
