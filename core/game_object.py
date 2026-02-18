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
        self._fall_landed = False

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
            if not self._fall_landed:
                self._fall_start_layer = self.current_layer
            self._fall_landed = False
            self.falling = True
            self._fall_timer = 0.0
        # Update target (may extend a fall already in progress)
        self._fall_target_layer = target_layer
        layers_fallen = max(1, self._fall_start_layer - target_layer)
        self._effective_fall_duration = max(
            self._min_fall_duration,
            self._fall_duration - self._fall_speed_increase * (layers_fallen - 1),
        )
