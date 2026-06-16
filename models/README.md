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

## Modelul folosit
- **Backbone:** MobileNet (NIMA aesthetic), antrenat pe setul **AVA**; greutăți din
  proiectul open-source *idealo/image-quality-assessment* (~3.2M parametri, ONNX ~13 MB).
- **Input:** imagine 224×224 RGB, NHWC (`1×224×224×3`). Scorer-ul detectează
  automat layout-ul (NCHW/NHWC) din metadatele ONNX. **Preprocesare: `[-1, 1]`**
  (`x/127.5 - 1`, specific MobileNet) — implementată în `photobackup/scoring.py`.
- **Output:** vector de **10** valori (distribuție peste scorurile 1–10).
  Scorer-ul calculează media ponderată → 1–10, apoi o mapează la 1–5 stele prin
  `config.RATING_THRESHOLDS`.

## Cum (re)generezi modelul
Pe o mașină de dezvoltare cu **Python 3.11** (conversia folosește TensorFlow):
```bash
python3.11 -m venv venv
./venv/bin/pip install "tensorflow==2.15.1" "tf2onnx==1.16.1" onnxruntime pillow
./venv/bin/python scripts/convert_nima_to_onnx.py      # descarcă greutățile + exportă models/nima.onnx
```
Apoi copiază modelul pe Pi (e prea mare pentru git — vezi `.gitignore`):
```bash
scp models/nima.onnx admin@photobackup.local:/home/admin/photobackup/models/
```
Rater-ul îl încarcă automat la următoarea evaluare (fără restart obligatoriu).

## Calibrare
După ce pui modelul, evaluează câteva sesiuni și, dacă distribuția stelelor e
prea „blândă"/„aspră", ajustează pragurile din `config.RATING_THRESHOLDS`
(implicit `[4.0, 4.75, 5.25, 5.75]`).
