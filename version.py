"""Version helpers for the Meshtastic MQTT Proxy fork."""

from pathlib import Path
import os
import subprocess


APP_NAME = "Meshtastic MQTT Proxy Fork"
FALLBACK_VERSION = "fork"


def _read_git_describe() -> str | None:
    """Return a git-based version string when repository metadata is available."""
    repo_root = Path(__file__).resolve().parent
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--dirty", "--always"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    version = result.stdout.strip()
    return version or None


def get_version() -> str:
    """Resolve a display version for local runs and bundled builds."""
    return os.environ.get("MQTT_PROXY_VERSION") or _read_git_describe() or FALLBACK_VERSION


__version__ = get_version()
