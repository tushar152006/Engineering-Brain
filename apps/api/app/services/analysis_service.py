"""Static analysis helpers — framework detection, entrypoint detection,
and directory summarization.

All functions return typed Pydantic-compatible dicts to match schema types.
"""

from collections import Counter
from pathlib import PurePosixPath

from app.models.schemas import Chunk

FRAMEWORK_MARKERS: dict[str, list[str]] = {
    "FastAPI":      ["fastapi", "uvicorn"],
    "Django":       ["django"],
    "Flask":        ["flask"],
    "React":        ["react", "react-dom"],
    "Next.js":      ["next", "next/router", "next/app"],
    "Vite":         ["vite", "vitejs"],
    "Express":      ["express"],
    "NestJS":       ["@nestjs"],
    "Prisma":       ["prisma", "@prisma"],
    "SQLAlchemy":   ["sqlalchemy"],
    "Tailwind CSS": ["tailwindcss"],
    "Docker":       ["dockerfile", "docker-compose"],
    "Pytest":       ["pytest", "conftest"],
    "TypeORM":      ["typeorm"],
    "GraphQL":      ["graphql", "apollo"],
    "Redis":        ["redis", "aioredis"],
    "Celery":       ["celery"],
    "Pydantic":     ["pydantic"],
}

ENTRYPOINT_FILES = {
    "main.py",
    "app.py",
    "server.py",
    "wsgi.py",
    "asgi.py",
    "index.js",
    "index.ts",
    "main.tsx",
    "main.jsx",
    "app.tsx",
    "app.jsx",
    "dockerfile",
    "docker-compose.yml",
    "compose.yml",
}


def detect_frameworks(chunks: list[Chunk]) -> list[dict[str, object]]:
    """Detect frameworks by scanning chunk content and file paths."""
    evidence: dict[str, set[str]] = {name: set() for name in FRAMEWORK_MARKERS}
    for chunk in chunks:
        haystack = f"{chunk.file_path}\n{chunk.content}".lower()
        for framework, markers in FRAMEWORK_MARKERS.items():
            if any(marker in haystack for marker in markers):
                evidence[framework].add(chunk.file_path)

    return [
        {"name": name, "evidence_files": sorted(files)[:5]}
        for name, files in evidence.items()
        if files
    ]


def detect_entrypoints(chunks: list[Chunk]) -> list[str]:
    """Detect likely application entrypoints by filename."""
    entrypoints: list[str] = []
    for chunk in chunks:
        name = PurePosixPath(chunk.file_path).name.lower()
        if name in ENTRYPOINT_FILES and chunk.file_path not in entrypoints:
            entrypoints.append(chunk.file_path)
    return entrypoints[:12]


def summarize_directories(chunks: list[Chunk]) -> list[dict[str, object]]:
    """Count chunks per top-level directory."""
    directories: Counter[str] = Counter()
    for chunk in chunks:
        path = PurePosixPath(chunk.file_path)
        if len(path.parts) > 1:
            directories[path.parts[0]] += 1

    return [{"name": name, "chunk_count": count} for name, count in directories.most_common(8)]
