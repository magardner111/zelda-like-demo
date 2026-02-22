class GameOptions:
    """Shared mutable game settings passed to menus and HUD."""

    def __init__(self):
        self.show_fps = True

    def save_to_dict(self):
        return {"show_fps": self.show_fps}

    def load_from_dict(self, data):
        self.show_fps = data.get("show_fps", True)
