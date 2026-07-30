"""
AquaMind AI — Phase 1 application package.

Ensures the repo-root `shared/` package (observability/reasoning_logger,
shared prompts, shared db docs) is always importable, regardless of the
process's current working directory or how this package is launched
(`python run.py`, `uvicorn app.main:app`, a Phase 2 service, pytest, etc).
"""
import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))          # .../phase1_standalone/app
_PHASE1_DIR = os.path.dirname(_APP_DIR)                          # .../phase1_standalone
_REPO_ROOT = os.path.dirname(_PHASE1_DIR)                        # .../aquamind-ai (repo root)

for _p in (_REPO_ROOT, _PHASE1_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
