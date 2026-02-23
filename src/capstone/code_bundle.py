from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from zipfile import ZipFile

TEXT_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".cs", ".c", ".cpp", ".h",
    ".hpp", ".go", ".rs", ".php", ".rb", ".sql", ".sh", ".ps1", ".md", ".yml", ".yaml", ".json"
}

SECRET_HINTS = (
    "api_key", "apikey", "secret", "token", "private_key", "authorization", "bearer "
)

@dataclass(frozen=True)
class BundledFile:
    path: str
    text: str
    truncated: bool

def _looks_textual(path: str) -> bool:
    return Path(path).suffix.lower() in TEXT_EXTS

def _redact_basic(text: str) -> str:
    lowered = text.lower()
    if any(hint in lowered for hint in SECRET_HINTS):
        lines = []
        for line in text.splitlines():
            l = line.lower()
            if any(hint in l for hint in SECRET_HINTS):
                lines.append("[REDACTED LINE POSSIBLE SECRET]")
            else:
                lines.append(line)
        return "\n".join(lines)
    return text

def bundle_code_from_zip(
    zip_path: Path,
    include_paths: Iterable[str],
    *,
    max_files: int = 10,
    max_total_chars: int = 150_000,
    max_file_chars: int = 30_000,
) -> list[BundledFile]:
    include_set = {p.replace("\\", "/").lstrip("/") for p in include_paths}
    results: list[BundledFile] = []
    total = 0

    with ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            p = info.filename.replace("\\", "/").lstrip("/")
            if p not in include_set:
                continue
            if not _looks_textual(p):
                continue

            raw = z.read(info)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="ignore")

            text = _redact_basic(text)

            truncated = False
            if len(text) > max_file_chars:
                text = text[:max_file_chars]
                truncated = True

            if total + len(text) > max_total_chars:
                remaining = max(0, max_total_chars - total)
                text = text[:remaining]
                truncated = True

            results.append(BundledFile(path=p, text=text, truncated=truncated))
            total += len(text)

            if len(results) >= max_files or total >= max_total_chars:
                break

    return results
