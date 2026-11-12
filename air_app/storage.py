"""Device-independent run locations and unique directory creation."""
from datetime import datetime
from pathlib import Path
import re
import uuid

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS = REPO_ROOT / 'runs'


def create_run_directory(root, name):
    stamp = datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S')
    slug = re.sub(r'[^\w.-]+', '-', name.strip()).strip('.-')[:80] or 'run'
    path = Path(root).expanduser() / f'{stamp}_{slug}_{uuid.uuid4().hex[:6]}'
    path.mkdir(parents=True, exist_ok=False)
    return path
