from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import image_content_namer as history_tools
import organize_files as core


APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
HISTORY_PATH = APP_DIR / "code_rename_history.json"
MAX_READ_BYTES = 120_000

CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".sql",
    ".r",
    ".m",
    ".lua",
    ".pl",
}

EXTENSION_LABELS = {
    ".py": "파이썬코드",
    ".js": "자바스크립트",
    ".jsx": "리액트화면",
    ".ts": "타입스크립트",
    ".tsx": "리액트화면",
    ".html": "웹페이지",
    ".htm": "웹페이지",
    ".css": "스타일시트",
    ".scss": "스타일시트",
    ".java": "자바코드",
    ".c": "C코드",
    ".h": "C헤더",
    ".cpp": "CPP코드",
    ".hpp": "CPP헤더",
    ".cs": "닷넷코드",
    ".go": "Go코드",
    ".rs": "Rust코드",
    ".php": "PHP코드",
    ".rb": "Ruby코드",
    ".swift": "Swift코드",
    ".kt": "Kotlin코드",
    ".kts": "Kotlin스크립트",
    ".sh": "쉘스크립트",
    ".ps1": "파워셸스크립트",
    ".bat": "배치스크립트",
    ".cmd": "명령스크립트",
    ".sql": "DB쿼리",
    ".r": "R분석코드",
    ".m": "매트랩코드",
    ".lua": "Lua코드",
    ".pl": "Perl코드",
}

KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "파일정리",
        (
            "fileorganizer",
            "file organizer",
            "organize_files",
            "cleanup_generated_dirs",
            "same_file_content",
            "shutil.move",
            "move and rename",
            "build_plan(",
            "apply_plan(",
        ),
    ),
    (
        "GUI앱",
        (
            "tkinter",
            "ttk.",
            "pyqt",
            "qwidget",
            "qmainwindow",
            "treeview",
            "messagebox",
            "drag",
            "drop",
            "button",
        ),
    ),
    (
        "이미지처리",
        (
            "image.open",
            "pillow",
            "from pil",
            "opencv",
            "cv2.",
            "ocr",
            "tesseract",
            "win_ocr",
            "thumbnail",
        ),
    ),
    (
        "API서버",
        (
            "fastapi",
            "flask",
            "express",
            "@app.route",
            "app.get(",
            "app.post(",
            "uvicorn",
            "router.",
        ),
    ),
    (
        "웹프론트",
        (
            "react",
            "usestate",
            "useeffect",
            "jsx",
            "tsx",
            "document.queryselector",
            "<html",
            "vue",
            "next/",
        ),
    ),
    (
        "데이터분석",
        (
            "pandas",
            "dataframe",
            "numpy",
            "matplotlib",
            "seaborn",
            "read_csv",
            "openpyxl",
            "xlsx",
        ),
    ),
    (
        "DB쿼리",
        (
            "select ",
            "insert into",
            "update ",
            "delete from",
            "create table",
            "join ",
            "sqlite",
            "sqlalchemy",
        ),
    ),
    (
        "테스트코드",
        (
            "unittest",
            "pytest",
            "assert ",
            "test_",
            "describe(",
            "it(",
            "expect(",
        ),
    ),
    (
        "모델학습",
        (
            "torch",
            "tensorflow",
            "sklearn",
            "fit(",
            "predict(",
            "model.train",
            "epochs",
        ),
    ),
    (
        "카메라비전",
        (
            "videocapture",
            "webcam",
            "camera",
            "yolo",
            "mediapipe",
            "cv2.imshow",
            "detect",
        ),
    ),
    (
        "실행스크립트",
        (
            "@echo off",
            "powershell",
            "start-process",
            "pyinstaller",
            "#!/bin/bash",
            "set -e",
            "param(",
        ),
    ),
    (
        "크롤링수집",
        (
            "requests.get",
            "beautifulsoup",
            "selenium",
            "playwright",
            "scrapy",
            "crawler",
        ),
    ),
    (
        "인증처리",
        (
            "jwt",
            "oauth",
            "login",
            "password",
            "auth",
            "session",
        ),
    ),
]

COMMON_SYMBOLS = {
    "main",
    "init",
    "run",
    "start",
    "stop",
    "get",
    "set",
    "handle",
    "process",
    "execute",
    "callback",
    "app",
    "index",
}


@dataclass(frozen=True)
class CodeRenameItem:
    source: Path
    destination: Path
    label: str
    reason: str
    action: str


@dataclass(frozen=True)
class CodeRestoreItem:
    source: Path
    destination: Path
    label: str
    reason: str
    action: str


def active_history_path(history_path: Path | None = None) -> Path:
    return history_path if history_path is not None else HISTORY_PATH


def is_code_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in CODE_EXTENSIONS


def iter_code_files(folder: Path, recursive: bool = True):
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    for path in iterator:
        if path.is_symlink() or not is_code_file(path):
            continue
        if ".file-organizer-logs" in path.parts:
            continue
        yield path


def read_code_text(path: Path) -> str:
    try:
        raw = path.read_bytes()[:MAX_READ_BYTES]
    except OSError:
        return ""
    if b"\x00" in raw:
        return ""
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def score_keyword_rules(text: str, path: Path) -> list[tuple[str, int]]:
    haystack = f"{path.name}\n{text}".lower()
    scores: list[tuple[str, int]] = []
    for label, terms in KEYWORD_RULES:
        score = 0
        for term in terms:
            hits = haystack.count(term)
            if hits:
                score += min(hits, 4)
        if score:
            scores.append((label, score))
    return sorted(scores, key=lambda item: item[1], reverse=True)


def split_identifier(value: str) -> list[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = value.replace("-", "_")
    parts = re.findall(r"[가-힣A-Za-z0-9]+", value)
    useful: list[str] = []
    for part in parts:
        lowered = part.lower()
        if lowered in COMMON_SYMBOLS or len(part) <= 1:
            continue
        useful.append(part)
        if len(useful) >= 3:
            break
    return useful


def symbol_label(text: str, path: Path) -> str:
    patterns = [
        r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(",
        r"\bconst\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=",
        r"\blet\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=",
        r"\bpublic\s+class\s+([A-Za-z_][A-Za-z0-9_]*)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            parts = split_identifier(match.group(1))
            if parts:
                return core.sanitize_segment("_".join(parts), fallback="", max_len=42)
    stem_parts = split_identifier(path.stem)
    if stem_parts:
        return core.sanitize_segment("_".join(stem_parts), fallback="", max_len=42)
    return ""


def suggested_code_name(path: Path) -> tuple[str, str]:
    text = read_code_text(path)
    scores = score_keyword_rules(text, path)
    if scores:
        labels = [scores[0][0]]
        if len(scores) > 1 and scores[1][1] >= 2:
            labels.append(scores[1][0])
        return core.sanitize_segment("_".join(labels), fallback="코드", max_len=42), "코드 키워드 분석"

    label = symbol_label(text, path)
    if label:
        return label, "함수/클래스 이름 분석"

    fallback = EXTENSION_LABELS.get(path.suffix.lower(), "코드")
    return fallback, "확장자 기준"


def unique_code_destination(source: Path, label: str, reserved: set[str]) -> Path:
    base = core.sanitize_segment(label, fallback="코드", max_len=48)
    dest = source.with_name(f"{base}{source.suffix}")
    counter = 2
    while core.norm_key(dest) in reserved or (dest.exists() and core.norm_key(dest) != core.norm_key(source)):
        dest = source.with_name(f"{base}_{counter:02d}{source.suffix}")
        counter += 1
    reserved.add(core.norm_key(dest))
    return dest


def build_code_rename_plan(folder: Path, recursive: bool = True) -> list[CodeRenameItem]:
    files = sorted(iter_code_files(folder, recursive=recursive), key=lambda item: str(item).lower())
    reserved: set[str] = set()
    plan: list[CodeRenameItem] = []
    for source in files:
        label, reason = suggested_code_name(source)
        destination = unique_code_destination(source, label, reserved)
        action = "skip" if core.norm_key(source) == core.norm_key(destination) else "rename"
        plan.append(CodeRenameItem(source, destination, label, reason, action))
    return plan


def remember_renames(renames: list[tuple[Path, Path, str]], history_path: Path | None = None) -> None:
    if not renames:
        return
    path = active_history_path(history_path)
    records = history_tools.load_history(path)
    timestamp = datetime.now().isoformat(timespec="seconds")
    for source, destination, label in renames:
        original = history_tools.find_original_path(source, records)
        records.append(
            {
                "timestamp": timestamp,
                "original": str(original),
                "renamed": str(destination),
                "label": label,
            }
        )
    history_tools.save_history(records, path)


def apply_code_rename_plan(
    plan: list[CodeRenameItem],
    record_history: bool = True,
    history_path: Path | None = None,
) -> dict[str, int]:
    counts = {"renamed": 0, "skipped": 0, "errors": 0}
    successful_renames: list[tuple[Path, Path, str]] = []
    for item in plan:
        if item.action != "rename":
            counts["skipped"] += 1
            continue
        try:
            item.source.rename(item.destination)
            counts["renamed"] += 1
            successful_renames.append((item.source, item.destination, item.label))
        except Exception:
            counts["errors"] += 1
    if record_history:
        remember_renames(successful_renames, history_path)
    return counts


def build_restore_plan(folder: Path, recursive: bool = True, history_path: Path | None = None) -> list[CodeRestoreItem]:
    records = history_tools.load_history(active_history_path(history_path))
    reserved: set[str] = set()
    seen_sources: set[str] = set()
    plan: list[CodeRestoreItem] = []
    for record in reversed(records):
        renamed = record.get("renamed")
        original = record.get("original")
        if not renamed or not original:
            continue
        source = Path(renamed)
        if not source.exists() or not source.is_file():
            continue
        if not history_tools.is_under_folder(source, folder):
            continue
        if not recursive and source.parent.resolve() != folder.resolve():
            continue
        source_key = history_tools.canonical(source)
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        original_path = Path(original)
        if core.norm_key(source) == core.norm_key(original_path):
            destination = original_path
        else:
            destination = history_tools.unique_restore_destination(original_path, reserved)
        action = "skip" if core.norm_key(source) == core.norm_key(destination) else "restore"
        plan.append(CodeRestoreItem(source, destination, original_path.stem, "코드 원본 이름 복구", action))
    return plan


def apply_restore_plan(plan: list[CodeRestoreItem], history_path: Path | None = None) -> dict[str, int]:
    counts = {"restored": 0, "skipped": 0, "errors": 0}
    restored_items: list[CodeRestoreItem] = []
    for item in plan:
        if item.action != "restore":
            counts["skipped"] += 1
            continue
        try:
            item.destination.parent.mkdir(parents=True, exist_ok=True)
            item.source.rename(item.destination)
            counts["restored"] += 1
            restored_items.append(item)
        except Exception:
            counts["errors"] += 1
    history_tools.remove_restored_history(restored_items, active_history_path(history_path))
    return counts
