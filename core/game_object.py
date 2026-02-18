import pygame


class GameObject:
    def __init__(self, position, stats):
        # -----------------------------
        # Position / Movement
        # -----------------------------
        self.pos = pygame.Vector2(position)
        self.vel = pygame.Vector2(0, 0)

        self.radius = stats["radius"]
        self.speed = stats["speed"]
        self.color = stats["color"]

        # IMPORTANT: default facing UP
        self.facing = pygame.Vector2(0, -1)

        # -----------------------------
        # Health
        # -----------------------------
        self.max_health = stats["max_health"]
        self.health = self.max_health

        # -----------------------------
        # Knockback
        # -----------------------------
        self.knockback_timer = 0.0

        # -----------------------------
        # Layer
        # -----------------------------
        self.current_layer = 0

        # -----------------------------
        # Edge Slide
        # -----------------------------
        self._slide_vel = pygame.Vector2(0, 0)

        # -----------------------------
        # Stairway cooldown (set externally by map_base)
        # -----------------------------
        self._stairway_cooldown = False

        # -----------------------------
        # Fall animation
        # -----------------------------
        self.falling = False
        self._fall_timer = 0.0
        self._fall_duration = stats.get("fall_duration", 0.6)
        self._fall_speed_increase = stats.get("fall_speed_increase", 0.2)
        self._min_fall_duration = stats.get("min_fall_duration", 0.3)
        self._effective_fall_duration = self._fall_duration
        self._fall_start_layer = 0
        self._fall_target_layer = 0

        # -----------------------------
        # Landing animation
        # -----------------------------
        self.landing = False
        self._land_timer = 0.0
        self._land_duration = stats.get("land_duration", 0.2)
        self._pending_shake = None
        self.camera_shake_enabled = True

    # =====================================================
    # KNOCKBACK
    # =====================================================

    def _update_knockback(self, dt):
        if self.knockback_timer > 0:
            self.knockback_timer -= dt
            self.pos += self.vel * dt
            self.vel *= 0.85

    # =====================================================
    # FALL
    # =====================================================

    def start_fall(self, target_layer):
        """Begin or extend the fall animation toward *target_layer*."""
        if not self.falling:
            if not self.landing:
                self._fall_start_layer = self.current_layer
            else:
                # Cancel an in-progress landing
                self.landing = False
            self.falling = True
            self._fall_timer = 0.0
        # Update target (may extend a fall already in progress)
        self._fall_target_layer = target_layer
        layers_fallen = max(1, self._fall_start_layer - target_layer)
        self._effective_fall_duration = max(
            self._min_fall_duration,
            self._fall_duration - self._fall_speed_increase * (layers_fallen - 1),
        )

    # =====================================================
    # LANDING
    # =====================================================

    def _start_landing(self):
        """Begin the landing animation (reverse of fall)."""
        self.landing = True
        self._land_timer = 0.0

    def _finish_landing(self):
        """Complete the landing — fire camera shake if enabled."""
        self.landing = False
        self._land_timer = 0.0
        if self.camera_shake_enabled:
            speed_ratio = 1.0 - (self._effective_fall_duration / self._fall_duration)
            self._pending_shake = (
                0.05 + speed_ratio * 0.5,
                3 + speed_ratio * 30,
            )

    def _update_fall(self, dt):
        """Tick fall/landing timers. Returns True if movement should be skipped."""
        if self.falling:
            self._fall_timer += dt
            if self._fall_timer >= self._effective_fall_duration:
                self.falling = False
                self._fall_timer = 0.0
                self.current_layer = self._fall_target_layer
                self._start_landing()
            return True

        if self.landing:
            self._land_timer += dt
            if self._land_timer >= self._land_duration:
                self._finish_landing()
            return True

        return False
