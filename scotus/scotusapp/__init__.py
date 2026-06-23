"""Leviathan SCOTUS research platform.

Note: we intentionally do NOT import ``config`` here. ``config`` pulls pydantic-settings and extends
sys.path with the sibling backend/ package; that bootstrap runs at runtime when ``scotusapp.db`` (or
anything importing ``scotusapp.config``) is loaded. Keeping ``__init__`` import-light lets the pure
analysis/segmentation unit tests run with only numpy + scikit-learn installed.
"""

__version__ = "0.1.0"
