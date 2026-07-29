"""
Wires up sys.path so any Phase 2 module can `import app.models`,
`import app.config`, etc. — the exact same Phase 1 modules, reused
unchanged (SDD Phase 2, Section 3.2 migration table: "no interface
changes").

Import this module FIRST, before importing anything from `app.*`, in every
Phase 2 entrypoint (service mains, gateway, scripts). It is idempotent and
side-effect-only (no exports needed).
"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))            # .../phase2_distributed/common
_PHASE2_DIR = os.path.dirname(_THIS_DIR)                           # .../phase2_distributed
_REPO_ROOT = os.path.dirname(_PHASE2_DIR)                          # .../aquamind-ai
_PHASE1_DIR = os.path.join(_REPO_ROOT, "phase1_standalone")

for _p in (_REPO_ROOT, _PHASE1_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
