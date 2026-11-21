"""RapidOCR (PP-OCRv5, English): a much better reader of game subtitles than the general Windows engine.

Measured on real game frames (experiments/real_frames_eval.py). Two settings matter for speed: the angle classifier
is skipped (subtitles are never upside down) and the text finder is told not to enlarge the picture (its default
doubles a subtitle strip, which made a reading take 1.9 s instead of 0.5 s on two cores).
"""

import logging
from pathlib import Path

import numpy as np

from dubzar.ocr import OcrLine

DET_MODEL = "PP-OCRv6_det_small.onnx"
REC_MODEL = "en_PP-OCRv5_rec_mobile.onnx"


def bundled_model_dir() -> Path:
    """Where the installer puts the two model files, so the app never needs to download them."""
    return Path(__file__).resolve().parent.parent / "models" / "rapidocr"


def engine_params(threads: int, det_max_side: int, model_dir: Path | None) -> dict:
    from rapidocr import LangRec, ModelType, OCRVersion

    params = {
        "Rec.lang_type": LangRec.EN, "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE,
        "Det.limit_type": "max", "Det.limit_side_len": det_max_side,
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }
    if model_dir is not None and (model_dir / DET_MODEL).exists() and (model_dir / REC_MODEL).exists():
        params["Det.model_path"] = str(model_dir / DET_MODEL)
        params["Rec.model_path"] = str(model_dir / REC_MODEL)
    return params


def stop_idle_spinning() -> None:
    """onnxruntime's worker threads busy-wait for work after every run: about one core burned between readings, which
    the game needs. Switch that off for the sessions RapidOCR creates (it exposes no setting for it)."""
    from rapidocr.inference_engine.onnxruntime.main import OrtInferSession

    if getattr(OrtInferSession, "_dubzar_no_spin", False):
        return
    original = OrtInferSession._init_sess_opts

    def patched(cfg):
        options = original(cfg)
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        return options

    OrtInferSession._init_sess_opts = staticmethod(patched)
    OrtInferSession._dubzar_no_spin = True


class RapidOcr:
    language = "en (PP-OCRv5)"

    def __init__(self, threads: int = 2, det_max_side: int = 1536, engine=None, model_dir: Path | None = None):
        if engine is None:
            from rapidocr import RapidOCR

            logging.getLogger("RapidOCR").setLevel(logging.ERROR)
            stop_idle_spinning()
            engine = RapidOCR(params=engine_params(threads, det_max_side, model_dir or bundled_model_dir()))
        self._engine = engine

    def read(self, image: np.ndarray) -> list[OcrLine]:
        height, width = image.shape[:2]
        output = self._engine(image, use_cls=False)
        if output.txts is None:
            return []
        lines = []
        scores = getattr(output, "scores", None)
        scores = scores if scores is not None else [0.0] * len(output.txts)
        for text, box, score in zip(output.txts, output.boxes, scores):
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            lines.append(OcrLine(text, (min(xs) + max(xs)) / 2 / width, (min(ys) + max(ys)) / 2 / height,
                                 (max(ys) - min(ys)) / height, float(score)))
        return lines
