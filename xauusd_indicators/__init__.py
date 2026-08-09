"""XAUUSD indicator + signal library. See docs/PRD.md for full scope,
docs/PROGRESS.md for what's verified against what, and pipeline.py for
the easiest entry point (compute_all_indicators / entry_signal /
exit_fired) if you don't need the individual indicator modules
directly.
"""
from .pipeline import Variant, compute_all_indicators, entry_signal, exit_fired

__version__ = "0.1.0"

__all__ = [
    "Variant",
    "compute_all_indicators",
    "entry_signal",
    "exit_fired",
    "__version__",
]
