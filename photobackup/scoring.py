"""Scor de calitate foto 1-5 stele.

Backend principal: NIMA (MobileNet) aesthetic via ONNX Runtime (CPU).
Fallback automat: euristica (claritate Laplacian + expunere + contrast) cu numpy,
cand modelul lipseste sau onnxruntime nu e instalat.
"""
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from . import config

log = logging.getLogger(__name__)

try:
    import onnxruntime as ort  # type: ignore
    _ORT_OK = True
except ImportError:
    _ORT_OK = False

_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def stars_from_mean(mean: float) -> int:
    """Mapare scor mediu NIMA (1-10) -> 1..5 stele prin pragurile din config."""
    for i, t in enumerate(config.RATING_THRESHOLDS):
        if mean < t:
            return i + 1
    return len(config.RATING_THRESHOLDS) + 1


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def heuristic_score(image: Image.Image) -> float:
    """Scor 1..5 din claritate/expunere/contrast (fara model)."""
    img = image.convert("L")
    # downscale pentru viteza (pastram detaliul suficient pentru claritate)
    img.thumbnail((1024, 1024))
    g = np.asarray(img, dtype=np.float64)
    if g.size < 9:
        return 3.0
    # claritate: varianta Laplacianului discret
    lap = (-4.0 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1]
           + g[1:-1, :-2] + g[1:-1, 2:])
    s_sharp = _clamp01(lap.var() / 1000.0)
    # expunere: aproape de mijloc = bine; clipping = penalizare
    mean = g.mean()
    s_expo = 1.0 - min(1.0, abs(mean - 128.0) / 128.0)
    clip = float((g < 8).mean() + (g > 247).mean())
    s_clip = 1.0 - min(1.0, clip * 3.0)
    # contrast
    s_contr = _clamp01(g.std() / 64.0)
    quality = 0.5 * s_sharp + 0.2 * s_expo + 0.15 * s_clip + 0.15 * s_contr
    return 1.0 + 4.0 * quality


class Scorer:
    """Incarca modelul NIMA o data; cade pe euristica daca nu e disponibil."""

    def __init__(self, model_path: Path = config.NIMA_MODEL):
        self.session = None
        self._input_name = None
        self._input_shape = None
        if _ORT_OK and Path(model_path).is_file():
            try:
                self.session = ort.InferenceSession(
                    str(model_path), providers=["CPUExecutionProvider"]
                )
                inp = self.session.get_inputs()[0]
                self._input_name = inp.name
                self._input_shape = inp.shape
                log.info("Scorer NIMA incarcat: %s (input %s)", model_path, inp.shape)
            except Exception as e:
                log.warning("Incarcare NIMA esuata (%s) — folosesc euristica", e)
                self.session = None
        else:
            log.info("NIMA indisponibil (onnxruntime=%s, model=%s) — euristica",
                     _ORT_OK, Path(model_path).is_file())

    @property
    def method(self) -> str:
        return "nima" if self.session is not None else "heuristic"

    def score(self, image: Image.Image) -> tuple[int, float, str]:
        """Returneaza (stele 1-5, scor_brut, metoda)."""
        if self.session is not None:
            try:
                mean = self._nima_mean(image)
                return stars_from_mean(mean), mean, "nima"
            except Exception as e:
                log.warning("Inferenta NIMA esuata (%s) — euristica", e)
        h = heuristic_score(image)
        return int(round(min(5.0, max(1.0, h)))), h, "heuristic"

    def _hw_layout(self) -> tuple[int, int, bool]:
        """Deduce (H, W, nchw) din shape-ul modelului; default 224x224 NCHW."""
        shape = self._input_shape or [1, 3, 224, 224]

        def _dim(v, default):
            return v if isinstance(v, int) and v > 0 else default

        if len(shape) == 4 and shape[1] == 3:  # NCHW
            return _dim(shape[2], 224), _dim(shape[3], 224), True
        if len(shape) == 4 and shape[3] == 3:  # NHWC
            return _dim(shape[1], 224), _dim(shape[2], 224), False
        return 224, 224, True

    def _nima_mean(self, image: Image.Image) -> float:
        h, w, nchw = self._hw_layout()
        rgb = image.convert("RGB").resize((w, h))
        arr = (np.asarray(rgb, dtype=np.float32) / 255.0 - _IMAGENET_MEAN) / _IMAGENET_STD
        arr = np.transpose(arr, (2, 0, 1)) if nchw else arr
        arr = np.expand_dims(arr, 0).astype(np.float32)
        out = self.session.run(None, {self._input_name: arr})[0]
        probs = np.asarray(out, dtype=np.float64).reshape(-1)
        if probs.size != 10:
            raise ValueError(f"output NIMA neasteptat: {probs.shape}")
        if probs.min() < 0 or abs(probs.sum() - 1.0) > 1e-3:  # aplicam softmax
            ex = np.exp(probs - probs.max())
            probs = ex / ex.sum()
        return float((probs * np.arange(1, 11)).sum())
