"""
Poller (SDD Section 20 folder layout: collector/poller.py).

The actual OS-level polling logic lives in collector/normalizer.py
(collect_raw_reading) since polling and normalising a single reading are a
single syscall-bound step in Phase 1. This module re-exports that entry
point under the name the SDD folder structure expects, and is the natural
place to add device-specific polling strategies later without touching
normalizer.py's schema-shaping logic.
"""
from collector.normalizer import collect_raw_reading

__all__ = ["collect_raw_reading"]
