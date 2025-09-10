from pathlib import Path
from rich.console import Console

# Configuration
ISOLATOR_DIR = Path.home() / ".isolator-apps"
IMAGES = ISOLATOR_DIR / "images"
CONTAINERS = ISOLATOR_DIR / "containers"
BIN = ISOLATOR_DIR / "bin"
LOGS = ISOLATOR_DIR / "logs"
DESKTOP_DIR = Path.home() / ".local/share/applications"
MAIN_LOG_FILE = LOGS / "isolator-main.log"
SUBPROCESS_LOG_FILE = LOGS / "isolator-subprocess.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3  # Keep 3 backup logs
console = Console()

# Ensure directories exist
for directory in [IMAGES, CONTAINERS, BIN, LOGS, DESKTOP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
