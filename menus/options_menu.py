from core.menu_base import Menu
from menus.controls_menu import ControlsMenu


class OptionsMenu(Menu):
    def __init__(self, options, back_callback, input_manager=None):
        self._options = options
        self._back_callback = back_callback
        self._controls_menu = None
        if input_manager is not None:
            self._controls_menu = ControlsMenu(input_manager, self._close_controls)
        items = [
            (self._fps_label(), self._toggle_fps),
            ("Controls",        self._open_controls),
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

    def _open_controls(self):
        if self._controls_menu is not None:
            self._controls_menu.open()

    def _close_controls(self):
        if self._controls_menu is not None:
            self._controls_menu.close()

    def update(self, input_manager):
        if self._controls_menu and self._controls_menu.active:
            self._controls_menu.update(input_manager)
        else:
            if input_manager.is_pressed("menu_back"):
                self._back_callback()
                return
            super().update(input_manager)

    def draw(self, screen):
        if self._controls_menu and self._controls_menu.active:
            self._controls_menu.draw(screen)
        else:
            super().draw(screen)
