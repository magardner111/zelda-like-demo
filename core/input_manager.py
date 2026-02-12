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
            "dodge": pygame.K_LCTRL,
            "sneak": pygame.K_LSHIFT,
            "menu": pygame.K_ESCAPE,
        }

        # Initialize key states safely
        self.keys = pygame.key.get_pressed()
        self.prev_keys = self.keys

        # -------------------------
        # Mouse configuration
        # -------------------------
        self.mouse_config = {
            "grab": True,
            "visible": False,
            "dead_zone": 5,
        }

        pygame.event.set_grab(self.mouse_config["grab"])
        pygame.mouse.set_visible(self.mouse_config["visible"])

        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())

    # =====================================================
    # UPDATE (call once per frame BEFORE player.update)
    # =====================================================

    def update(self):
        self.prev_keys = self.keys
        self.keys = pygame.key.get_pressed()
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())

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

    # =====================================================
    # MOUSE
    # =====================================================

    def get_mouse_pos(self):
        return pygame.Vector2(self.mouse_pos)
