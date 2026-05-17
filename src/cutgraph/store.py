from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from .schema import CutGraphProject, ProjectSettings


PROJECT_FILENAME = ".cutgraph.json"


def project_file(project_root: Path | str) -> Path:
    return Path(project_root).joinpath(PROJECT_FILENAME)


def create_project(project_root: Path | str) -> CutGraphProject:
    root = Path(project_root)
    root.mkdir(parents=True, exist_ok=True)
    project = CutGraphProject(settings=ProjectSettings())
    save_project(root, project)
    return project


def load_project(project_root: Path | str) -> CutGraphProject:
    path = project_file(project_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Project file not found: {path}") from exc
    except JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    try:
        return CutGraphProject.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid CutGraph project in {path}: {exc}") from exc


def save_project(project_root: Path | str, project: CutGraphProject) -> None:
    root = Path(project_root)
    root.mkdir(parents=True, exist_ok=True)
    path = project_file(root)
    tmp_path = path.with_suffix(".json.tmp")
    payload = project.model_dump(mode="json")
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
