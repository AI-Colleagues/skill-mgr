"""Adapter exports."""

from skill_mgr.adapters.bundled import bundled_adapter_matrix, bundled_adapters
from skill_mgr.adapters.registry import resolve_targets


__all__ = ["bundled_adapter_matrix", "bundled_adapters", "resolve_targets"]
