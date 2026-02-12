import pygame
import sys

from core.menu_base import Menu


class MainMenu(Menu):
    def __init__(self, config=None):
        self._input_manager = None
        items = [
            ("Continue", self._continue),
            ("Dummy", None),
            ("Quit", self._quit),
        ]
        super().__init__(items, config)

    def _continue(self):
        self.close(self._input_manager)

    def _quit(self):
        pygame.quit()
        sys.exit()

    def open(self, input_manager=None):
        if input_manager:
            self._input_manager = input_manager
        super().open()

    def close(self, input_manager=None):
        super().close(input_manager or self._input_manager)
