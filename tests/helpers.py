"""Test helpers — importlib-based plugin module loaders.

Plugin directories contain hyphens (polza-balance, image-gen),
making standard ``import`` impossible.  These helpers load the
modules via ``importlib.util.spec_from_file_location`` so unit
tests can import from production code instead of duplicating it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

# ── polza-balance ────────────────────────────────────────────────────
# No external dependencies beyond stdlib, safe to load at module scope.

_balance_init = _REPO / "plugins" / "polza-balance" / "__init__.py"
_bal_spec = importlib.util.spec_from_file_location(
    "polza_balance_src",
    str(_balance_init),
)
polza_balance = importlib.util.module_from_spec(_bal_spec)
_bal_spec.loader.exec_module(polza_balance)
sys.modules["polza_balance_src"] = polza_balance

# ── image_gen _utils ─────────────────────────────────────────────────
# Pure functions extracted to _utils.py — no Hermes dependencies.

_image_utils = _REPO / "plugins" / "image_gen" / "polza" / "_utils.py"
_img_spec = importlib.util.spec_from_file_location(
    "image_gen_utils_src",
    str(_image_utils),
)
image_gen_utils = importlib.util.module_from_spec(_img_spec)
_img_spec.loader.exec_module(image_gen_utils)
sys.modules["image_gen_utils_src"] = image_gen_utils
