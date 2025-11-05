"""Shared fixtures for hook tests."""
import shutil
from pathlib import Path
import pytest


@pytest.fixture(scope="function", autouse=True)
def ensure_hooks_installed():
    """Ensure real hooks are installed before each test."""
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".claude" / "hooks"
    templates_dir = project_root / "templates" / "hooks"
    skill_rules_template = project_root / "templates" / "skill-rules.json"
    skill_rules_target = project_root / ".claude" / "skill-rules.json"

    # Always ensure hooks are installed
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for hook_file in templates_dir.glob("*.sh"):
        target = hooks_dir / hook_file.name
        # Only copy if missing or wrong size (corrupted)
        if not target.exists() or target.stat().st_size < 100:
            shutil.copy(hook_file, target)
            target.chmod(0o755)

    # Ensure skill rules exist
    if not skill_rules_target.exists():
        shutil.copy(skill_rules_template, skill_rules_target)

    yield
