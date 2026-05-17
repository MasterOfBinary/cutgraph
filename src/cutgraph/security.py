from __future__ import annotations

from pathlib import Path


class PathPolicyError(ValueError):
    """Raised when a user path violates CutGraph project boundaries."""


class ProjectPaths:
    def __init__(
        self,
        project_root: Path | str,
        *,
        render_dir: str = "renders",
        cache_dir: str = ".cutgraph/cache",
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.render_dir = render_dir
        self.cache_dir = cache_dir

    def resolve_project_path(self, path: Path | str) -> Path:
        candidate = self._resolve(path)
        if not candidate.is_relative_to(self.project_root):
            raise PathPolicyError(f"Path {path!s} is outside project root")
        return candidate

    def resolve_render_output(self, path: Path | str) -> Path:
        candidate = self.resolve_project_path(path)
        allowed_root = self.project_root.joinpath(self.render_dir).resolve()
        if not candidate.is_relative_to(allowed_root):
            raise PathPolicyError(
                f"Render output {path!s} must be inside {self.render_dir}/"
            )
        return candidate

    def resolve_cache_path(self, path: Path | str) -> Path:
        candidate = self.resolve_project_path(path)
        allowed_root = self.project_root.joinpath(self.cache_dir).resolve()
        if not candidate.is_relative_to(allowed_root):
            raise PathPolicyError(
                f"Cache path {path!s} must be inside {self.cache_dir}/"
            )
        return candidate

    def _resolve(self, path: Path | str) -> Path:
        raw = Path(path)
        if raw.is_absolute():
            return raw.resolve()
        return self.project_root.joinpath(raw).resolve()
