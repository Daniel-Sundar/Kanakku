import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from loader import load_folder  # noqa: E402


@pytest.fixture
def example():
    return load_folder(str(ROOT / "data" / "example"))
