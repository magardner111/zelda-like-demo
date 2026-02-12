import pygame


class InputManager:
    def __init__(self):
        # -------------------------
        # Action → Key bindings
        # -------------------------
        self.keymap = {
            "move_up": pygame.K_w,
            "move_down": pygame.K_s,
            "move_left": pygame.K_a,
            "move_right": pygame.K_d,
            "sword": pygame.K_SPACE,
            "arrow": pygame.K_e,
        }

        # Initialize key states safely
        self.keys = pygame.key.get_pressed()
        self.prev_keys = self.keys

    # =====================================================
    # UPDATE (call once per frame BEFORE player.update)
    # =====================================================

    def update(self):
        self.prev_keys = self.keys
        self.keys = pygame.key.get_pressed()

    # =====================================================
    # HELD DOWN (continuous)
    # =====================================================

    def is_down(self, action):
        key = self.keymap.get(action)
        if key is None:
            return False
        return self.keys[key]

    # =====================================================
    # PRESSED THIS FRAME (edge detection)
    # =====================================================

    def is_pressed(self, action):
        key = self.keymap.get(action)
        if key is None:
            return False

        return self.keys[key] and not self.prev_keys[key]

    # =====================================================
    # RELEASED THIS FRAME
    # =====================================================

    def is_released(self, action):
        key = self.keymap.get(action)
        if key is None:
            return False

        return not self.keys[key] and self.prev_keys[key]
