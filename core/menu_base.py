import pygame


class Menu:
    def __init__(self, items, config=None):
        """
        items: list of (label, callback) tuples
        config: optional dict with normal_color, selected_color, font_size, item_spacing
        """
        config = config or {}
        self.normal_color = config.get("normal_color", (255, 255, 255))
        self.selected_color = config.get("selected_color", (100, 149, 237))
        self.font_size = config.get("font_size", 48)
        self.item_spacing = config.get("item_spacing", 60)

        self.items = items
        self.selected_index = 0
        self.active = False
        self.font = pygame.font.SysFont(None, self.font_size)
        self.item_rects = []

        self._prev_enter = False
        self._prev_click = False

    def open(self):
        self.active = True
        self.selected_index = 0
        # Suppress any held keys / mouse buttons so the press that opened
        # this menu doesn't immediately trigger an item.
        self._prev_enter = True
        self._prev_click = True
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

    def close(self, input_manager=None):
        self.active = False
        if input_manager:
            pygame.event.set_grab(input_manager.mouse_config["grab"])
            pygame.mouse.set_visible(input_manager.mouse_config["visible"])

    def update(self, input_manager):
        if not self.active:
            return

        # Navigation via mapped move keys (WASD or remapped)
        if input_manager.is_pressed("move_up"):
            self.selected_index = (self.selected_index - 1) % len(self.items)
        if input_manager.is_pressed("move_down"):
            self.selected_index = (self.selected_index + 1) % len(self.items)

        # Arrow keys always work for menu navigation regardless of remapping
        if input_manager.keys[pygame.K_UP] and not input_manager.prev_keys[pygame.K_UP]:
            self.selected_index = (self.selected_index - 1) % len(self.items)
        if input_manager.keys[pygame.K_DOWN] and not input_manager.prev_keys[pygame.K_DOWN]:
            self.selected_index = (self.selected_index + 1) % len(self.items)

        # Mouse hover detection
        mouse_pos = pygame.mouse.get_pos()
        for i, rect in enumerate(self.item_rects):
            if rect.collidepoint(mouse_pos):
                self.selected_index = i
                break

        # Confirm: Enter/Space on keyboard, B/Y on gamepad
        if input_manager.is_pressed("menu_confirm"):
            self._trigger(self.selected_index)
            return

        # Mouse click
        if pygame.mouse.get_pressed()[0]:
            if not self._prev_click:
                for i, rect in enumerate(self.item_rects):
                    if rect.collidepoint(mouse_pos):
                        self._trigger(i)
                        break
        self._prev_click = pygame.mouse.get_pressed()[0]

    def _trigger(self, index):
        _, callback = self.items[index]
        if callback:
            callback()

    def draw(self, screen):
        if not self.active:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Render menu items
        self.item_rects = []
        screen_w, screen_h = screen.get_size()
        total_height = len(self.items) * self.item_spacing
        start_y = (screen_h - total_height) // 2

        for i, (label, _) in enumerate(self.items):
            color = self.selected_color if i == self.selected_index else self.normal_color
            text_surface = self.font.render(label, True, color)
            rect = text_surface.get_rect(center=(screen_w // 2, start_y + i * self.item_spacing))
            screen.blit(text_surface, rect)
            self.item_rects.append(rect)
