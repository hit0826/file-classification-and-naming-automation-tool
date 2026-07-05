from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import image_content_namer as history_tools
import organize_files as core


APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
HISTORY_PATH = APP_DIR / "document_rename_history.json"
MAX_READ_BYTES = 180_000

DOCUMENT_EXTENSIONS = {
    ".md",
    ".txt",
    ".log",
    ".csv",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".docx",
}

STOPWORDS = {
    "그리고",
    "그러나",
    "또한",
    "위한",
    "기반",
    "이용",
    "통해",
    "대한",
    "관련",
    "설명",
    "문서",
    "시스템",
    "구현",
    "과정",
    "구성",
    "역할",
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
}

KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("드론_정밀착륙_YOLO", ("드론", "drone", "정밀 착륙", "precision landing", "landing", "착륙", "yolo", "픽스호크", "pixhawk", "라즈베리파이", "raspberry pi", "mavlink")),
    ("라즈베리파이_픽스호크_연동", ("라즈베리파이", "raspberry pi", "픽스호크", "pixhawk", "미션플래너", "mission planner", "mavproxy")),
    ("연구논문_초안", ("논문", "초록", "abstract", "서론", "결론", "참고문헌")),
    ("프로젝트_보고서", ("보고서", "목적", "결과", "분석", "개선")),
    ("회의_기록", ("회의", "참석", "안건", "논의", "결정")),
    ("일정_계획", ("일정", "계획", "마감", "진행", "schedule")),
    ("계약_문서", ("계약", "agreement", "contract", "조항")),
    ("이력서_자기소개", ("이력서", "자기소개", "경력", "지원동기")),
]


@dataclass(frozen=True)
class DocumentRenameItem:
    source: Path
    destination: Path
    label: str
    reason: str
    action: str


@dataclass(frozen=True)
class DocumentRestoreItem:
    source: Path
    destination: Path
    label: str
    reason: str
    action: str


def active_history_path(history_path: Path | None = None) -> Path:
    return history_path if history_path is not None else HISTORY_PATH


def is_document_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in DOCUMENT_EXTENSIONS


def iter_document_files(folder: Path, recursive: bool = True):
    iterator = folder.rglob("*") if recursive else folder.iterdir()
    for path in iterator:
        if path.is_symlink() or not is_document_file(path):
            continue
        if ".file-organizer-logs" in path.parts:
            continue
        yield path


def read_text_file(path: Path) -> str:
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


def read_docx_text(path: Path) -> str:
    try:
        with ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except Exception:
        return ""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return ""
    text_nodes = []
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for node in root.iter(namespace + "t"):
        if node.text:
            text_nodes.append(node.text)
    return "\n".join(text_nodes)


def read_document_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return read_docx_text(path)
    return read_text_file(path)


def normalize_text(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[#>*_\[\]()`~]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_meaningful_line(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip().strip("#>*- \t")
        if not line:
            continue
        if re.fullmatch(r"[-=]{3,}", line):
            continue
        if len(line) >= 6:
            return line
    return ""


def score_keyword_rules(text: str) -> list[tuple[str, int]]:
    haystack = text.lower()
    scores: list[tuple[str, int]] = []
    for label, terms in KEYWORD_RULES:
        score = 0
        for term in terms:
            hits = haystack.count(term.lower())
            if hits:
                score += min(hits, 5)
        if score:
            scores.append((label, score))
    return sorted(scores, key=lambda item: item[1], reverse=True)


def title_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", text)
    useful: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in STOPWORDS or len(token) <= 1:
            continue
        if re.fullmatch(r"20\d{2}", token):
            continue
        if token not in useful:
            useful.append(token)
        if len(useful) >= 5:
            break
    return useful


def suggested_document_name(path: Path) -> tuple[str, str]:
    text = read_document_text(path)
    if not text.strip():
        return "문서", "내용 읽기 실패"

    first_line = first_meaningful_line(text)
    scores = score_keyword_rules(f"{first_line}\n{text}")
    if scores and scores[0][1] >= 3:
        return core.sanitize_segment(scores[0][0], fallback="문서", max_len=54), "문서 키워드 분석"

    tokens = title_tokens(first_line)
    if not tokens:
        tokens = title_tokens(normalize_text(text))
    if tokens:
        return core.sanitize_segment("_".join(tokens), fallback="문서", max_len=54), "문서 제목 분석"

    return core.sanitize_segment(path.stem, fallback="문서", max_len=54), "기존 이름 기준"


def unique_document_destination(source: Path, label: str, reserved: set[str]) -> Path:
    base = core.sanitize_segment(label, fallback="문서", max_len=54)
    dest = source.with_name(f"{base}{source.suffix.lower()}")
    counter = 2
    while core.norm_key(dest) in reserved or (dest.exists() and core.norm_key(dest) != core.norm_key(source)):
        dest = source.with_name(f"{base}_{counter:02d}{source.suffix.lower()}")
        counter += 1
    reserved.add(core.norm_key(dest))
    return dest


def build_document_rename_plan(folder: Path, recursive: bool = True) -> list[DocumentRenameItem]:
    files = sorted(iter_document_files(folder, recursive=recursive), key=lambda item: str(item).lower())
    reserved: set[str] = set()
    plan: list[DocumentRenameItem] = []
    for source in files:
        label, reason = suggested_document_name(source)
        destination = unique_document_destination(source, label, reserved)
        action = "skip" if core.norm_key(source) == core.norm_key(destination) else "rename"
        plan.append(DocumentRenameItem(source, destination, label, reason, action))
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


def apply_document_rename_plan(
    plan: list[DocumentRenameItem],
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


def build_restore_plan(folder: Path, recursive: bool = True, history_path: Path | None = None) -> list[DocumentRestoreItem]:
    records = history_tools.load_history(active_history_path(history_path))
    reserved: set[str] = set()
    seen_sources: set[str] = set()
    plan: list[DocumentRestoreItem] = []
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
        plan.append(DocumentRestoreItem(source, destination, original_path.stem, "문서 원본 이름 복구", action))
    return plan


def apply_restore_plan(plan: list[DocumentRestoreItem], history_path: Path | None = None) -> dict[str, int]:
    counts = {"restored": 0, "skipped": 0, "errors": 0}
    restored_items: list[DocumentRestoreItem] = []
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
