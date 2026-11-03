"""Explicit daily-input preparation; no automatic scientific corrections."""

from .daily_inputs import read_daily_depths
from .source_mapping import prepare_source_volumes

__all__ = ["read_daily_depths", "prepare_source_volumes"]
