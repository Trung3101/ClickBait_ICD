import os
import shutil
import threading
from pathlib import Path


_segmenter = None
_segmenter_lock = threading.Lock()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_vncorenlp_path() -> Path:
    source_path = _repo_root() / "vncorenlp_data"
    target_path = source_path
    if " " in str(source_path):
        target_path = Path.home() / ".cache" / "vncorenlp_data"
        if source_path.exists():
            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
    return target_path


def infer_java_home_from_executable(java_executable: str | os.PathLike[str]) -> Path:
    java_path = Path(java_executable)
    if java_path.parent.name.lower() == "bin":
        return java_path.parent.parent
    return java_path.parent


def _find_java_home() -> Path | None:
    for executable in ("javac", "java"):
        resolved = shutil.which(executable)
        if resolved:
            return infer_java_home_from_executable(resolved)

    java_root = Path("C:/Program Files/Java")
    if java_root.exists():
        candidates = sorted(java_root.glob("jdk*"), reverse=True)
        if candidates:
            return candidates[0]
    return None


def ensure_java_home() -> None:
    if os.environ.get("JAVA_HOME"):
        return
    java_home = _find_java_home()
    if java_home is not None and java_home.exists():
        os.environ["JAVA_HOME"] = str(java_home)


def get_segmenter():
    global _segmenter
    if _segmenter is not None:
        return _segmenter

    with _segmenter_lock:
        if _segmenter is not None:
            return _segmenter

        ensure_java_home()

        import py_vncorenlp

        model_path = _resolve_vncorenlp_path()
        model_path.mkdir(parents=True, exist_ok=True)
        if not any(model_path.iterdir()):
            py_vncorenlp.download_model(save_dir=str(model_path))

        original_cwd = os.getcwd()
        try:
            _segmenter = py_vncorenlp.VnCoreNLP(annotators=["wseg"], save_dir=str(model_path))
        finally:
            os.chdir(original_cwd)

        return _segmenter


def segment_text(text: str) -> str:
    value = "" if text is None else str(text).strip()
    if not value:
        return ""
    return " ".join(get_segmenter().word_segment(value)).strip()
