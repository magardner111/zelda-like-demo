"""Registry mapping pattern type strings to their module/class/default params.

Uses lazy imports so the editor (Tkinter) doesn't need to import pygame.
"""

import importlib

PATTERN_REGISTRY = {
    "up_down": {
        "module": "patterns.enemy_patterns",
        "class_name": "UpDownPattern",
        "params": {"distance": 200, "pause_time": 2.5, "speed": 60},
    },
}


def get_pattern_class(ptype):
    """Return the pattern class for the given type string."""
    entry = PATTERN_REGISTRY[ptype]
    mod = importlib.import_module(entry["module"])
    return getattr(mod, entry["class_name"])
