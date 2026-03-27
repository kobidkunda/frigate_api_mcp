from __future__ import annotations

import sys
from pathlib import Path


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
MAIN_REPO_ROOT = WORKTREE_ROOT.parent.parent

# Ensure tests import the worktree package first, not the main checkout.
sys.path = [p for p in sys.path if Path(p).resolve() != MAIN_REPO_ROOT.resolve()]
sys.path.insert(0, str(WORKTREE_ROOT))
