"""Simple file-based document store for MVP.

Stores original files and serialized DocumentGraphs on the local filesystem.
Can be swapped for S3 + PostgreSQL in production.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from docunav.models.document import DocumentGraph, Extraction

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path("./docunav_storage")


class DocumentStore:
    """Local filesystem store for documents and graphs."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_STORAGE_DIR
        self.files_dir = self.base_dir / "files"
        self.graphs_dir = self.base_dir / "graphs"
        self.extractions_dir = self.base_dir / "extractions"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
        self.extractions_dir.mkdir(parents=True, exist_ok=True)

    # -- Files --

    def store_file(self, file_path: Path, file_id: str) -> Path:
        dest = self.files_dir / file_id / file_path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(file_path), str(dest))
        return dest

    def store_file_bytes(self, data: bytes, filename: str, file_id: str) -> Path:
        dest = self.files_dir / file_id / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest

    def get_file_path(self, file_id: str, filename: str) -> Path | None:
        path = self.files_dir / file_id / filename
        return path if path.exists() else None

    # -- DocumentGraphs --

    def save_graph(self, graph: DocumentGraph) -> Path:
        path = self.graphs_dir / f"{graph.document.id}.json"
        path.write_text(graph.model_dump_json(indent=2))
        return path

    def load_graph(self, file_id: str) -> DocumentGraph | None:
        path = self.graphs_dir / f"{file_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return DocumentGraph.model_validate(data)

    def list_graphs(self) -> list[str]:
        return [p.stem for p in self.graphs_dir.glob("*.json")]

    def delete_graph(self, file_id: str) -> bool:
        path = self.graphs_dir / f"{file_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # -- Extractions --

    def save_extraction(self, extraction: Extraction) -> Path:
        path = self.extractions_dir / f"{extraction.id}.json"
        path.write_text(extraction.model_dump_json(indent=2))
        return path

    def load_extraction(self, extraction_id: str) -> Extraction | None:
        path = self.extractions_dir / f"{extraction_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Extraction.model_validate(data)

    def list_extractions(self, document_id: str | None = None) -> list[str]:
        ids: list[str] = []
        for p in self.extractions_dir.glob("*.json"):
            if document_id:
                data = json.loads(p.read_text())
                if data.get("document_id") == document_id:
                    ids.append(p.stem)
            else:
                ids.append(p.stem)
        return ids
