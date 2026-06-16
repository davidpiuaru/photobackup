"""Construieste modelul NIMA (idealo MobileNet aesthetic) si il exporta in ONNX.

Modelul: MobileNet (224x224) -> Dropout -> Dense(10, softmax), antrenat pe setul
AVA pentru scor estetic. Greutatile provin din proiectul open-source
idealo/image-quality-assessment. Iesirea e o distributie peste scorurile 1-10;
scorer-ul (photobackup/scoring.py) calculeaza media si o mapeaza la 1-5 stele.

A se rula pe o masina de dezvoltare (Mac/PC) cu Python 3.11:
    python3.11 -m venv venv && ./venv/bin/pip install \
        "tensorflow==2.15.1" "tf2onnx==1.16.1" onnxruntime pillow
    ./venv/bin/python scripts/convert_nima_to_onnx.py
Apoi copiaza rezultatul pe Pi:
    scp models/nima.onnx admin@photobackup.local:/home/admin/photobackup/models/
    sudo systemctl restart photobackup-api   # optional

IMPORTANT: preprocesarea la inferenta trebuie sa fie [-1, 1] (MobileNet),
asa cum e implementata in photobackup/scoring.py.
"""
import os
import urllib.request

import tensorflow as tf
import tf2onnx
from tensorflow.keras.applications import MobileNet
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.models import Model

WEIGHTS_URL = (
    "https://github.com/idealo/image-quality-assessment/raw/master/"
    "models/MobileNet/weights_mobilenet_aesthetic_0.07.hdf5"
)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = os.path.join(_ROOT, "models", "weights_mobilenet_aesthetic.hdf5")
OUT = os.path.join(_ROOT, "models", "nima.onnx")


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if not os.path.exists(WEIGHTS):
        print("Descarc greutatile idealo (AVA aesthetic)...")
        urllib.request.urlretrieve(WEIGHTS_URL, WEIGHTS)

    base = MobileNet(input_shape=(224, 224, 3), weights=None,
                     include_top=False, pooling="avg")
    x = Dropout(0.0)(base.output)
    x = Dense(10, activation="softmax")(x)
    model = Model(base.inputs, x)
    model.load_weights(WEIGHTS)
    print(f"Model construit: {model.count_params():,} parametri")

    spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="input"),)
    tf2onnx.convert.from_keras(model, input_signature=spec, opset=13, output_path=OUT)
    print("ONNX salvat la:", OUT)


if __name__ == "__main__":
    main()
