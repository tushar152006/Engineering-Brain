import io
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import SourceFile

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".md": "markdown",
    ".mdx": "markdown",
    ".txt": "text",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".ini": "ini",
    ".env.example": "env",
    ".dockerfile": "dockerfile",
}

IGNORED_PARTS = {
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

IGNORED_FILENAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
}


def infer_language(path: str) -> str | None:
    lower_path = path.lower()
    name = Path(lower_path).name
    if name == "dockerfile":
        return "dockerfile"
    if name in IGNORED_FILENAMES:
        return None
    suffix = Path(lower_path).suffix
    if lower_path.endswith(".env.example"):
        return "env"
    return SUPPORTED_EXTENSIONS.get(suffix)


def is_ignored_path(path: str) -> bool:
    parts = set(Path(path).parts)
    return bool(parts.intersection(IGNORED_PARTS))


def decode_text(data: bytes, path: str) -> str | None:
    if b"\x00" in data:
        return None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def normalize_github_url(url: str) -> tuple[str, list[str]]:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        raise HTTPException(status_code=400, detail="Only github.com repository URLs are supported")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="GitHub URL must include owner and repository")

    owner, repo = parts[0], re.sub(r"\.git$", "", parts[1])
    branch = "/".join(parts[3:]) if len(parts) > 3 and parts[2] == "tree" else None
    branches = [branch] if branch else ["main", "master"]
    display_name = f"{owner}/{repo}"
    archive_urls = [
        f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{item}" for item in branches
    ]
    return display_name, archive_urls


class RepositoryLoader:
    async def load_github_zip(self, url: str) -> tuple[str, list[SourceFile], int]:
        display_name, archive_urls = normalize_github_url(url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = None
            for archive_url in archive_urls:
                candidate = await client.get(archive_url)
                if candidate.status_code == 200:
                    response = candidate
                    break

            if response is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Could not download repository archive. "
                        "Check the URL and default branch."
                    ),
                )

        files, skipped = self._read_zip(response.content)
        return display_name, files, skipped

    def load_local_path(
        self,
        local_path: str,
        name: str | None,
    ) -> tuple[str, list[SourceFile], int]:
        if not settings.enable_local_repo_import:
            raise HTTPException(status_code=403, detail="Local repository import is disabled")

        root = Path(local_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise HTTPException(status_code=400, detail="Local path must be an existing directory")

        files: list[SourceFile] = []
        skipped = 0
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel_path = path.relative_to(root).as_posix()
            if is_ignored_path(rel_path):
                skipped += 1
                continue
            language = infer_language(rel_path)
            if language is None:
                skipped += 1
                continue
            size = path.stat().st_size
            if size > settings.max_index_file_bytes:
                skipped += 1
                continue
            content = decode_text(path.read_bytes(), rel_path)
            if not content:
                skipped += 1
                continue
            files.append(
                SourceFile(
                    path=rel_path,
                    language=language,
                    content=content,
                    size_bytes=size,
                )
            )

        return name or root.name, files, skipped

    def _read_zip(self, data: bytes) -> tuple[list[SourceFile], int]:
        files: list[SourceFile] = []
        skipped = 0
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                raw_path = member.filename
                rel_parts = Path(raw_path).parts[1:]
                if not rel_parts:
                    skipped += 1
                    continue
                rel_path = Path(*rel_parts).as_posix()
                if is_ignored_path(rel_path):
                    skipped += 1
                    continue
                language = infer_language(rel_path)
                if language is None:
                    skipped += 1
                    continue
                if member.file_size > settings.max_index_file_bytes:
                    skipped += 1
                    continue
                with archive.open(member) as file:
                    content = decode_text(file.read(), rel_path)
                if not content:
                    skipped += 1
                    continue
                files.append(
                    SourceFile(
                        path=rel_path,
                        language=language,
                        content=content,
                        size_bytes=member.file_size,
                    )
                )
        return files, skipped


repository_loader = RepositoryLoader()
