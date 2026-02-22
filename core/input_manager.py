import pygame

# Default keyboard bindings (used for reset)
DEFAULT_KEYMAP = {
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

# Default gamepad button -> action mapping
# Keys can be int (button index) or str ("LT"/"RT" for trigger axes).
# NOTE: Buttons 0(A), 1(B), 3(Y) are used as fixed menu navigation
# (A=back, B/Y=confirm), so gameplay actions avoid those by default.
DEFAULT_GAMEPAD_MAP = {
    "RT": "sword",    # Right Trigger
    5:    "arrow",    # RB
    4:    "dodge",    # LB
    "LT": "sneak",   # Left Trigger
    7:    "menu",     # Start
}

# Display names for buttons and virtual trigger keys
BUTTON_NAMES = {
    0: "A", 1: "B", 2: "X", 3: "Y",
    4: "LB", 5: "RB", 6: "Back", 7: "Start",
    8: "Guide", 9: "L3", 10: "R3",
    "LT": "LT", "RT": "RT",
}

STICK_DEAD_ZONE = 0.25
TRIGGER_THRESHOLD = 0.5

# Axis indices
RIGHT_STICK_X_AXIS = 3
RIGHT_STICK_Y_AXIS = 4
LEFT_TRIGGER_AXIS = 2
RIGHT_TRIGGER_AXIS = 5  # may not exist on all controllers


class InputManager:
    def __init__(self):
        # -------------------------
        # Action -> Key bindings (mutable copy)
        # -------------------------
        self.keymap = dict(DEFAULT_KEYMAP)

        # Initialize key states safely
        self.keys = pygame.key.get_pressed()
        self.prev_keys = self.keys

        # -------------------------
        # Merged action state (keyboard OR gamepad)
        # -------------------------
        actions = list(self.keymap.keys()) + ["menu_confirm", "menu_back"]
        self.action_state = {a: False for a in actions}
        self.prev_action_state = {a: False for a in actions}

        # -------------------------
        # Gamepad
        # -------------------------
        pygame.joystick.init()
        self.joystick = None
        # Don't detect here — events haven't been pumped yet.
        # First detection happens in update() after the event loop runs.

        self.gamepad_map = dict(DEFAULT_GAMEPAD_MAP)

        # Right stick direction (unit vector or zero)
        self.right_stick = pygame.Vector2(0, 0)
        # True once right stick is used; suppresses mouse facing until
        # the mouse itself moves again.
        self.right_stick_active = False
        self._last_mouse_pos = pygame.Vector2(pygame.mouse.get_pos())

        # Input mode: "keyboard" or "controller" (both always work;
        # this just controls what the Controls menu displays)
        self.input_mode = "keyboard"

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
    # JOYSTICK DETECTION (hot-plug)
    # =====================================================

    def _detect_joystick(self):
        """Try to grab the first connected joystick.  Called every frame
        when we don't currently have one so hot-plug works."""
        count = pygame.joystick.get_count()
        if count > 0:
            js = pygame.joystick.Joystick(0)
            js.init()
            self.joystick = js
        else:
            self.joystick = None

    # =====================================================
    # CONFIG SAVE / LOAD
    # =====================================================

    def save_to_dict(self):
        """Return a JSON-safe dict of all remappable state."""
        # JSON keys must be strings; int button indices get stringified.
        gp = {str(k): v for k, v in self.gamepad_map.items()}
        return {
            "keymap": {action: key for action, key in self.keymap.items()},
            "gamepad_map": gp,
            "input_mode": self.input_mode,
        }

    def load_from_dict(self, data):
        """Restore keymap, gamepad_map, input_mode from a dict."""
        if "keymap" in data:
            for action, key in data["keymap"].items():
                if action in self.keymap:
                    self.keymap[action] = int(key)
        if "gamepad_map" in data:
            self.gamepad_map = {}
            for btn_str, action in data["gamepad_map"].items():
                # Restore int keys where possible; keep "LT"/"RT" as strings.
                try:
                    btn = int(btn_str)
                except ValueError:
                    btn = btn_str
                self.gamepad_map[btn] = action
        if "input_mode" in data:
            self.input_mode = data["input_mode"]

    # =====================================================
    # KEY REMAPPING (keyboard)
    # =====================================================

    def rebind_key(self, action, new_key):
        """Rebind *action* to *new_key*, swapping with any action that
        previously used *new_key* to avoid duplicate bindings."""
        old_key = self.keymap[action]
        for other_action, k in self.keymap.items():
            if k == new_key and other_action != action:
                self.keymap[other_action] = old_key
                break
        self.keymap[action] = new_key

    # =====================================================
    # BUTTON REMAPPING (gamepad)
    # =====================================================

    def rebind_button(self, action, new_button):
        """Rebind *action* to *new_button*, swapping with any action that
        previously used *new_button* to avoid duplicates."""
        old_button = None
        for btn, act in self.gamepad_map.items():
            if act == action:
                old_button = btn
                break
        if old_button is None:
            return
        # Swap if another action already owns new_button
        if new_button in self.gamepad_map:
            self.gamepad_map[old_button] = self.gamepad_map[new_button]
        else:
            del self.gamepad_map[old_button]
        self.gamepad_map[new_button] = action

    def get_button_for_action(self, action):
        """Return the button index currently bound to *action*, or None."""
        for btn, act in self.gamepad_map.items():
            if act == action:
                return btn
        return None

    # =====================================================
    # RESET
    # =====================================================

    def reset_defaults(self):
        self.keymap = dict(DEFAULT_KEYMAP)
        self.gamepad_map = dict(DEFAULT_GAMEPAD_MAP)

    # =====================================================
    # UPDATE (call once per frame BEFORE player.update)
    # =====================================================

    def update(self):
        self.prev_keys = self.keys
        self.keys = pygame.key.get_pressed()
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())

        # Hot-plug: re-check joystick each frame when we don't have one
        if self.joystick is None:
            self._detect_joystick()
        else:
            try:
                if not self.joystick.get_init():
                    self.joystick = None
                    self._detect_joystick()
            except pygame.error:
                self.joystick = None

        # Build merged action state
        self.prev_action_state = dict(self.action_state)

        # Start with keyboard state
        for action, key in self.keymap.items():
            self.action_state[action] = bool(self.keys[key])

        # Reset right stick
        self.right_stick = pygame.Vector2(0, 0)

        # Merge gamepad state (OR)
        if self.joystick is not None:
            try:
                num_buttons = self.joystick.get_numbuttons()
                num_axes = self.joystick.get_numaxes()

                # Buttons and trigger axes (using mutable gamepad_map)
                for btn, action in self.gamepad_map.items():
                    if isinstance(btn, int):
                        # Real button
                        if btn < num_buttons and self.joystick.get_button(btn):
                            self.action_state[action] = True
                    elif btn == "LT":
                        if (num_axes > LEFT_TRIGGER_AXIS
                                and self.joystick.get_axis(LEFT_TRIGGER_AXIS) > TRIGGER_THRESHOLD):
                            self.action_state[action] = True
                    elif btn == "RT":
                        if (num_axes > RIGHT_TRIGGER_AXIS
                                and self.joystick.get_axis(RIGHT_TRIGGER_AXIS) > TRIGGER_THRESHOLD):
                            self.action_state[action] = True

                # Left stick -> movement
                if num_axes >= 2:
                    axis_x = self.joystick.get_axis(0)
                    axis_y = self.joystick.get_axis(1)
                    if axis_x < -STICK_DEAD_ZONE:
                        self.action_state["move_left"] = True
                    if axis_x > STICK_DEAD_ZONE:
                        self.action_state["move_right"] = True
                    if axis_y < -STICK_DEAD_ZONE:
                        self.action_state["move_up"] = True
                    if axis_y > STICK_DEAD_ZONE:
                        self.action_state["move_down"] = True

                # D-pad (hat) -> movement
                if self.joystick.get_numhats() > 0:
                    hat_x, hat_y = self.joystick.get_hat(0)
                    if hat_x < 0:
                        self.action_state["move_left"] = True
                    if hat_x > 0:
                        self.action_state["move_right"] = True
                    if hat_y > 0:
                        self.action_state["move_up"] = True
                    if hat_y < 0:
                        self.action_state["move_down"] = True

                # Right stick -> facing direction
                if num_axes > max(RIGHT_STICK_X_AXIS, RIGHT_STICK_Y_AXIS):
                    rx = self.joystick.get_axis(RIGHT_STICK_X_AXIS)
                    ry = self.joystick.get_axis(RIGHT_STICK_Y_AXIS)
                    if abs(rx) > STICK_DEAD_ZONE or abs(ry) > STICK_DEAD_ZONE:
                        self.right_stick = pygame.Vector2(rx, ry)
                        if self.right_stick.length() > 0:
                            self.right_stick = self.right_stick.normalize()

            except pygame.error:
                # Joystick disconnected mid-frame
                self.joystick = None

        # Auto-detect input mode based on which device was used this frame.
        # Any newly pressed keyboard key → keyboard mode.
        # Any gamepad button/stick/trigger activity → controller mode.
        _any_key = False
        for k in range(len(self.keys)):
            if self.keys[k] and not self.prev_keys[k]:
                _any_key = True
                break
        if _any_key:
            self.input_mode = "keyboard"
        elif self.joystick is not None:
            _any_gp = False
            try:
                for i in range(self.joystick.get_numbuttons()):
                    if self.joystick.get_button(i):
                        _any_gp = True
                        break
                if not _any_gp and self.joystick.get_numaxes() >= 2:
                    if (abs(self.joystick.get_axis(0)) > STICK_DEAD_ZONE
                            or abs(self.joystick.get_axis(1)) > STICK_DEAD_ZONE):
                        _any_gp = True
                if not _any_gp and self.joystick.get_numaxes() > LEFT_TRIGGER_AXIS:
                    if self.joystick.get_axis(LEFT_TRIGGER_AXIS) > TRIGGER_THRESHOLD:
                        _any_gp = True
                if not _any_gp and self.joystick.get_numaxes() > RIGHT_TRIGGER_AXIS:
                    if self.joystick.get_axis(RIGHT_TRIGGER_AXIS) > TRIGGER_THRESHOLD:
                        _any_gp = True
            except pygame.error:
                pass
            if _any_gp:
                self.input_mode = "controller"

        # Track right stick ownership of facing direction.
        # Once the right stick is deflected, it "owns" facing until the
        # mouse physically moves, at which point the mouse takes over again.
        if self.right_stick.length_squared() > 0:
            self.right_stick_active = True
        if self.mouse_pos != self._last_mouse_pos:
            self.right_stick_active = False
        self._last_mouse_pos = pygame.Vector2(self.mouse_pos)

        # Fixed menu actions (bypass remappable keymap / gamepad_map)
        # Keyboard: Enter or Space to confirm, Backspace to go back
        self.action_state["menu_confirm"] = (
            bool(self.keys[pygame.K_RETURN])
            or bool(self.keys[pygame.K_SPACE])
        )
        self.action_state["menu_back"] = bool(self.keys[pygame.K_BACKSPACE])

        # Gamepad: B(1) or Y(3) to confirm, A(0) to go back (fixed buttons)
        if self.joystick is not None:
            try:
                nb = self.joystick.get_numbuttons()
                if nb > 1 and self.joystick.get_button(1):
                    self.action_state["menu_confirm"] = True
                if nb > 3 and self.joystick.get_button(3):
                    self.action_state["menu_confirm"] = True
                if nb > 0 and self.joystick.get_button(0):
                    self.action_state["menu_back"] = True
            except pygame.error:
                pass

    # =====================================================
    # HELD DOWN (continuous)
    # =====================================================

    def is_down(self, action):
        return self.action_state.get(action, False)

    # =====================================================
    # PRESSED THIS FRAME (edge detection)
    # =====================================================

    def is_pressed(self, action):
        return (self.action_state.get(action, False)
                and not self.prev_action_state.get(action, False))

    # =====================================================
    # RELEASED THIS FRAME
    # =====================================================

    def is_released(self, action):
        return (not self.action_state.get(action, False)
                and self.prev_action_state.get(action, False))

    # =====================================================
    # MOUSE
    # =====================================================

    def get_mouse_pos(self):
        return pygame.Vector2(self.mouse_pos)
