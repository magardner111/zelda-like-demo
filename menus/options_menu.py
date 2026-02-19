from core.menu_base import Menu


class OptionsMenu(Menu):
    def __init__(self, options, back_callback):
        self._options = options
        items = [
            (self._fps_label(), self._toggle_fps),
            ("Back",            back_callback),
        ]
        super().__init__(items)

    # --- helpers ---

    def _fps_label(self):
        state = "ON" if self._options.show_fps else "OFF"
        return f"Show FPS:  {state}"

    def _toggle_fps(self):
        self._options.show_fps = not self._options.show_fps
        self.items[0] = (self._fps_label(), self._toggle_fps)
