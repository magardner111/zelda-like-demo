import pygame
import sys

from core.menu_base import Menu
from menus.options_menu import OptionsMenu


class MainMenu(Menu):
    def __init__(self, options=None, config=None, input_manager=None,
                 quit_callback=None, close_callback=None):
        self._input_manager = input_manager
        self._options = options
        self._quit_callback = quit_callback
        self._close_callback = close_callback
        items = [
            ("Continue", self._continue),
            ("Options",  self._open_options),
            ("Quit",     self._quit),
        ]
        super().__init__(items, config)
        self._options_menu = OptionsMenu(
            options, self._close_options, input_manager=input_manager
        )

    def _continue(self):
        self.close(self._input_manager)

    def _open_options(self):
        self._options_menu.open()

    def _close_options(self):
        # Only deactivate the sub-menu; the main menu stays open
        self._options_menu.close()

    def _quit(self):
        if self._quit_callback:
            self._quit_callback()
        pygame.quit()
        sys.exit()

    def open(self, input_manager=None):
        if input_manager:
            self._input_manager = input_manager
        super().open()

    def close(self, input_manager=None):
        super().close(input_manager or self._input_manager)
        if self._close_callback:
            self._close_callback()

    def update(self, input_manager):
        if self._options_menu.active:
            self._options_menu.update(input_manager)
        else:
            if input_manager.is_pressed("menu_back"):
                self._continue()
                return
            super().update(input_manager)

    def draw(self, screen):
        if self._options_menu.active:
            self._options_menu.draw(screen)
        else:
            super().draw(screen)
