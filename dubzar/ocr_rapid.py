"""RapidOCR (PP-OCRv5, English): a much better reader of game subtitles than the general Windows engine.

Measured on real game frames (experiments/real_frames_eval.py). Two settings matter for speed: the angle classifier
is skipped (subtitles are never upside down) and the text finder is told not to enlarge the picture (its default
doubles a subtitle strip, which made a reading take 1.9 s instead of 0.5 s on two cores).
"""

import logging
import os
import sys
from pathlib import Path

import numpy as np

from dubzar.ocr import OcrLine

DET_MODEL = "PP-OCRv6_det_small.onnx"
REC_MODEL = "en_PP-OCRv5_rec_mobile.onnx"


def bundled_model_dir() -> Path:
    """Where the installer puts the two model files, so the app never needs to download them."""
    return Path(__file__).resolve().parent.parent / "models" / "rapidocr"


def engine_params(threads: int, det_max_side: int, model_dir: Path | None, gpu: bool = False) -> dict:
    from rapidocr import LangRec, ModelType, OCRVersion

    params = {
        "Rec.lang_type": LangRec.EN, "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE,
        "Det.limit_type": "max", "Det.limit_side_len": det_max_side,
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }
    if gpu:
        params["EngineConfig.onnxruntime.use_cuda"] = True
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


def _cuda_library_folders() -> list[str]:
    """Folders that may hold the CUDA 12 / cuDNN 9 libraries: the nvidia pip packages and a torch installation."""
    folders = []
    for base in sys.path:
        nvidia = Path(base) / "nvidia"
        if nvidia.is_dir():
            folders += [str(p) for p in nvidia.glob("*/bin") if p.is_dir()]
        torch_lib = Path(base) / "torch" / "lib"
        if torch_lib.is_dir():
            folders.append(str(torch_lib))
    return folders


def _a_model_file(model_dir: Path) -> Path | None:
    """A recognizer model to try the graphics card with: the shipped one, or the one the library keeps itself."""
    shipped = model_dir / REC_MODEL
    if shipped.exists():
        return shipped
    try:
        import rapidocr

        own = Path(rapidocr.__file__).parent / "models" / REC_MODEL
        return own if own.exists() else None
    except ImportError:
        return None


def cuda_ready(model: Path | None) -> bool:
    """Can onnxruntime really run on the graphics card here? Looks for the libraries and tries a session."""
    try:
        import onnxruntime as ort

        if "CUDAExecutionProvider" not in ort.get_available_providers():
            return False
        for folder in _cuda_library_folders():
            try:
                os.add_dll_directory(folder)
                os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
            except (OSError, AttributeError):
                pass
        if model is None or not Path(model).exists():
            return False
        session = ort.InferenceSession(str(model), providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        return session.get_providers()[0] == "CUDAExecutionProvider"
    except Exception as exc:  # no card, no libraries, a driver that is too old: the processor reads instead
        logging.getLogger(__name__).info("ekran kartıyla okuma kullanılamıyor: %s", exc)
        return False


class RapidOcr:
    language = "en (PP-OCRv5)"

    def __init__(self, threads: int = 2, det_max_side: int = 1536, engine=None, model_dir: Path | None = None,
                 gpu: bool = False):
        model_dir = model_dir or bundled_model_dir()
        if gpu and not cuda_ready(_a_model_file(model_dir)):
            logging.getLogger(__name__).info("ekran kartı bulunamadı: okuma işlemciyle yapılacak")
            gpu = False
        self.gpu = gpu
        if gpu:
            self.language = "en (PP-OCRv5, GPU)"
        if engine is None:
            from rapidocr import RapidOCR

            logging.getLogger("RapidOCR").setLevel(logging.ERROR)
            stop_idle_spinning()
            engine = RapidOCR(params=engine_params(threads, det_max_side, model_dir, gpu))
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
