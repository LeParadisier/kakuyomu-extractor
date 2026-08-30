"""Project folder and file structure manager."""

import shutil
from pathlib import Path


def initialize_project_folders(project_dir: Path, enable_ai: bool, default_prompt_src: Path) -> Path:
    """Create directory structure without deleting existing content."""
    project_dir = project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Core folders
    (project_dir / "toc").mkdir(exist_ok=True)
    (project_dir / "raw").mkdir(exist_ok=True)

    # AI folders
    if enable_ai:
        (project_dir / "AI_translated").mkdir(exist_ok=True)
        prompt_dir = project_dir / "system_prompt"
        prompt_dir.mkdir(exist_ok=True)

        target_prompt = prompt_dir / "default.txt"
        if not target_prompt.exists() and default_prompt_src.exists():
            shutil.copy(default_prompt_src, target_prompt)

    return project_dir