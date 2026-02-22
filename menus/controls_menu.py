import pygame

from core.menu_base import Menu
from core.input_manager import (
    BUTTON_NAMES, TRIGGER_THRESHOLD, LEFT_TRIGGER_AXIS, RIGHT_TRIGGER_AXIS,
)

# Actions that can be remapped on keyboard (exclude "menu")
REMAPPABLE_ACTIONS = [
    "move_up",
    "move_down",
    "move_left",
    "move_right",
    "sword",
    "arrow",
    "dodge",
    "sneak",
]

# Actions that map to gamepad buttons (remappable)
BUTTON_ACTIONS = ["sword", "arrow", "dodge", "sneak"]

# Movement is stick/D-pad (read-only display)
MOVEMENT_ACTIONS = ["move_up", "move_down", "move_left", "move_right"]

# Friendly display names
ACTION_LABELS = {
    "move_up":    "Move Up",
    "move_down":  "Move Down",
    "move_left":  "Move Left",
    "move_right": "Move Right",
    "sword":      "Sword",
    "arrow":      "Arrow",
    "dodge":      "Dodge",
    "sneak":      "Sneak",
}

# Fixed controller movement labels
CONTROLLER_MOVEMENT = {
    "move_up":    "Stick Up / D-Pad Up",
    "move_down":  "Stick Down / D-Pad Down",
    "move_left":  "Stick Left / D-Pad Left",
    "move_right": "Stick Right / D-Pad Right",
}

# Cooldown (ms) after opening before input is accepted
OPEN_COOLDOWN_MS = 25


def _button_name(btn):
    return BUTTON_NAMES.get(btn, f"Button {btn}")


class ControlsMenu(Menu):
    def __init__(self, input_manager, back_callback):
        self._input_manager = input_manager
        self._back_callback = back_callback
        self._binding_action = None       # None = browse, str = bind mode
        self._binding_type = None         # "key" or "button"
        self._prev_keys_raw = None        # snapshot for key bind mode
        self._prev_buttons_raw = None     # snapshot for button bind mode
        self._open_tick = 0

        items = self._build_items()
        config = {"font_size": 36, "item_spacing": 45}
        super().__init__(items, config)

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------

    def open(self):
        super().open()
        self._open_tick = pygame.time.get_ticks()
        self._binding_action = None
        self._binding_type = None
        self._prev_keys_raw = None
        self._prev_buttons_raw = None

    # ------------------------------------------------------------------
    # Item list builders
    # ------------------------------------------------------------------

    def _build_items(self):
        items = []
        if self._input_manager.input_mode == "keyboard":
            items += self._keyboard_items()
        else:
            items += self._controller_items()
        items.append(("Reset Defaults", self._reset_defaults))
        items.append(("Back", self._back_callback))
        return items

    # --- Keyboard items ---

    def _keyboard_items(self):
        items = []
        for action in REMAPPABLE_ACTIONS:
            items.append((self._kb_label(action), self._make_key_select(action)))
        return items

    def _kb_label(self, action):
        key = self._input_manager.keymap[action]
        key_name = pygame.key.name(key).upper()
        return f"{ACTION_LABELS[action]}:  {key_name}"

    def _make_key_select(self, action):
        def _select():
            self._enter_key_bind_mode(action)
        return _select

    # --- Controller items ---

    def _controller_items(self):
        items = []
        # Movement — read-only (stick / D-pad)
        for action in MOVEMENT_ACTIONS:
            label = f"{ACTION_LABELS[action]}:  {CONTROLLER_MOVEMENT[action]}"
            items.append((label, None))
        # Button actions — rebindable
        for action in BUTTON_ACTIONS:
            items.append((self._btn_label(action), self._make_btn_select(action)))
        return items

    def _btn_label(self, action):
        btn = self._input_manager.get_button_for_action(action)
        name = _button_name(btn) if btn is not None else "---"
        return f"{ACTION_LABELS[action]}:  {name}"

    def _make_btn_select(self, action):
        def _select():
            self._enter_button_bind_mode(action)
        return _select

    # ------------------------------------------------------------------
    # Rebuild
    # ------------------------------------------------------------------

    def _rebuild(self):
        old_index = self.selected_index
        self.items = self._build_items()
        self.selected_index = min(old_index, len(self.items) - 1)

    # ------------------------------------------------------------------
    # Bind modes
    # ------------------------------------------------------------------

    def _enter_key_bind_mode(self, action):
        self._binding_action = action
        self._binding_type = "key"
        self._prev_keys_raw = pygame.key.get_pressed()

    def _enter_button_bind_mode(self, action):
        js = self._input_manager.joystick
        if js is None:
            return  # no controller connected, do nothing
        self._binding_action = action
        self._binding_type = "button"
        self._prev_keys_raw = pygame.key.get_pressed()
        self._prev_buttons_raw = [
            js.get_button(i) for i in range(js.get_numbuttons())
        ]
        # Snapshot trigger axis state so a held trigger isn't captured
        self._prev_triggers = self._read_triggers(js)

    @staticmethod
    def _read_triggers(js):
        """Return dict of trigger key -> bool (past threshold)."""
        num_axes = js.get_numaxes()
        return {
            "LT": (num_axes > LEFT_TRIGGER_AXIS
                   and js.get_axis(LEFT_TRIGGER_AXIS) > TRIGGER_THRESHOLD),
            "RT": (num_axes > RIGHT_TRIGGER_AXIS
                   and js.get_axis(RIGHT_TRIGGER_AXIS) > TRIGGER_THRESHOLD),
        }

    def _exit_bind_mode(self):
        self._binding_action = None
        self._binding_type = None
        self._prev_keys_raw = None
        self._prev_buttons_raw = None
        self._prev_triggers = None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _reset_defaults(self):
        self._input_manager.reset_defaults()
        self._rebuild()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, input_manager):
        if not self.active:
            return

        # Cooldown: ignore all input briefly after opening
        if pygame.time.get_ticks() - self._open_tick < OPEN_COOLDOWN_MS:
            return

        if self._binding_action is not None:
            if self._binding_type == "key":
                self._update_key_bind()
            else:
                self._update_button_bind()
        else:
            if input_manager.is_pressed("menu_back"):
                self._back_callback()
                return
            super().update(input_manager)

    def _update_key_bind(self):
        keys = pygame.key.get_pressed()
        prev = self._prev_keys_raw

        # Escape cancels
        if keys[pygame.K_ESCAPE] and not prev[pygame.K_ESCAPE]:
            self._exit_bind_mode()
            return

        # Detect first newly pressed key
        for key_code in range(len(keys)):
            if keys[key_code] and not prev[key_code]:
                self._input_manager.rebind_key(self._binding_action, key_code)
                self._rebuild()
                self._exit_bind_mode()
                return

        self._prev_keys_raw = keys

    def _update_button_bind(self):
        js = self._input_manager.joystick
        if js is None:
            self._exit_bind_mode()
            return

        # Escape on keyboard cancels
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] and not self._prev_keys_raw[pygame.K_ESCAPE]:
            self._exit_bind_mode()
            return
        self._prev_keys_raw = keys

        # Detect first newly pressed gamepad button
        num = min(js.get_numbuttons(), len(self._prev_buttons_raw))
        for i in range(num):
            pressed = js.get_button(i)
            if pressed and not self._prev_buttons_raw[i]:
                self._input_manager.rebind_button(self._binding_action, i)
                self._rebuild()
                self._exit_bind_mode()
                return

        self._prev_buttons_raw = [
            js.get_button(i) for i in range(js.get_numbuttons())
        ]

        # Detect newly pulled triggers
        triggers = self._read_triggers(js)
        for trig_key in ("LT", "RT"):
            if triggers[trig_key] and not self._prev_triggers.get(trig_key, False):
                self._input_manager.rebind_button(self._binding_action, trig_key)
                self._rebuild()
                self._exit_bind_mode()
                return

        self._prev_triggers = triggers

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        if not self.active:
            return

        super().draw(screen)

        if self._binding_action is not None:
            label = ACTION_LABELS.get(self._binding_action, self._binding_action)
            if self._binding_type == "key":
                prompt = f"Press a key for {label}..."
            else:
                prompt = f"Press a button for {label}..."
            prompt_color = (255, 255, 100)
            text_surface = self.font.render(prompt, True, prompt_color)
            screen_w, screen_h = screen.get_size()
            rect = text_surface.get_rect(center=(screen_w // 2, screen_h // 2 - 200))
            bg = pygame.Surface((rect.width + 20, rect.height + 10), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 200))
            screen.blit(bg, (rect.x - 10, rect.y - 5))
            screen.blit(text_surface, rect)
