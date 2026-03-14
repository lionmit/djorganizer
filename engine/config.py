# engine/config.py
"""Config file I/O and path validation."""
from pathlib import Path
from typing import Optional, Dict
import platform

BLOCKED_PATHS = {
    Path("/"), Path("/System"), Path("/usr"), Path("/bin"),
    Path("/sbin"), Path("/etc"),
}
if platform.system() == "Windows":
    BLOCKED_PATHS.update({
        Path("C:\\Windows"), Path("C:\\Program Files"),
        Path("C:\\Program Files (x86)"),
    })

DEFAULT_CONFIG = {
    "source_folder": "",
    "output_folder": "",
    "genres_enabled": "all",
    "locale_genres": "auto",
    "filename_suffix": "false",
    "copy_mode": "true",
}

def validate_path(path: Path) -> bool:
    """Reject system-critical paths and symlinks outside scope."""
    resolved = path.resolve()
    for blocked in BLOCKED_PATHS:
        try:
            blocked_resolved = blocked.resolve()
            # Exact match: path IS the blocked path
            if resolved == blocked_resolved:
                return False
            # Ancestry match: path is INSIDE a blocked path
            # Skip root ("/") for ancestry — it's a parent of everything
            if blocked_resolved != Path("/").resolve() and blocked_resolved in resolved.parents:
                return False
        except (OSError, ValueError):
            pass
    return True

def load_config(config_file: Path) -> Optional[Dict[str, str]]:
    """Load config from key=value file. Returns None if file missing."""
    if not config_file.exists():
        return None
    config = {}
    for line in config_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()
    return config

ALLOWED_CONFIG_KEYS = set(DEFAULT_CONFIG.keys())

def save_config(config: dict, config_file: Path):
    """Save config to key=value file. Only allowed keys are persisted."""
    lines = ["# DJOrganizer v19 settings — delete this file to reconfigure\n"]
    for key, val in config.items():
        if key not in ALLOWED_CONFIG_KEYS:
            continue
        safe_val = str(val).replace('\n', '').replace('\r', '')
        lines.append(f"{key} = {safe_val}\n")
    config_file.write_text("".join(lines), encoding="utf-8")
