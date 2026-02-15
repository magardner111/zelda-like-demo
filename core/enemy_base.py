import math

import pygame

# Half-angle cosine for enemy sight cone (120° FOV → 60° half-angle)
_SIGHT_COS = math.cos(math.radians(60))


class Enemy:
    def __init__(self, position, stats):
        # -----------------------------
        # Position
        # -----------------------------
        self.pos = pygame.Vector2(position)

        # -----------------------------
        # Stats
        # -----------------------------
        self.size = stats["size"]
        self.radius = self.size
        self.speed = stats["speed"]
        self.max_health = stats["max_health"]
        self.health = self.max_health
        self.color = stats["color"]

        self.hit_damage = stats.get("hit_damage", 1)

        # -----------------------------
        # Alert / Chase
        # -----------------------------
        self.alert_radius = stats.get("alert_radius", 150)
        self.chase_speed = stats.get("chase_speed", 80)
        self.alert_cooldown = stats.get("alert_cooldown", 3.0)
        self.knockback_resistance = stats.get("knockback_resistance", 0)

        self.phase = "pattern"  # "pattern" or "alerted"
        self.alert_timer = 0.0
        self._last_known_player_pos = None

        # -----------------------------
        # Knockback
        # -----------------------------
        self.vel = pygame.Vector2(0, 0)
        self.knockback_timer = 0.0

        # -----------------------------
        # Damage Flash
        # -----------------------------
        self.flash_timer = 0.0
        self.flash_duration = 0.1

        # -----------------------------
        # Layer
        # -----------------------------
        self.current_layer = 0

        # -----------------------------
        # Visibility fade
        # -----------------------------
        self.visibility_alpha = 255

        # -----------------------------
        # Facing
        # -----------------------------
        self.facing = pygame.Vector2(0, 1)  # default: face down

        # -----------------------------
        # Pattern (None for now)
        # -----------------------------
        self.pattern = None

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, dt, player, solid_regions):
        detected = self._detect_player(player, solid_regions)

        if self.phase == "pattern":
            if detected:
                self.phase = "alerted"
                self.alert_timer = self.alert_cooldown
                self._last_known_player_pos = pygame.Vector2(player.pos)
            elif self.pattern:
                self.pattern.update(self, dt)
        elif self.phase == "alerted":
            if detected:
                self._last_known_player_pos = pygame.Vector2(player.pos)
                self.alert_timer = self.alert_cooldown
            else:
                self.alert_timer -= dt

            # Move toward player (or last known position)
            target = self._last_known_player_pos
            if target:
                direction = target - self.pos
                if direction.length_squared() > 0:
                    direction = direction.normalize()
                    self.facing = pygame.Vector2(direction)
                    self.pos += direction * self.chase_speed * dt

            if self.alert_timer <= 0:
                self.phase = "pattern"
                self.alert_timer = 0.0
                self._last_known_player_pos = None
                # Re-anchor pattern at current position
                if self.pattern:
                    self.pattern.start_pos = None

        # Knockback movement
        if self.knockback_timer > 0:
            self.knockback_timer -= dt
            self.pos += self.vel * dt
            self.vel *= 0.85

        if self.flash_timer > 0:
            self.flash_timer -= dt

    # =====================================================
    # DETECTION
    # =====================================================

    def _detect_player(self, player, solid_regions):
        """Check if this enemy can detect the player."""
        if player.current_layer != self.current_layer:
            return False

        if player.sneaking:
            # Sneaking: only detectable within enemy's sight cone
            to_player = player.pos - self.pos
            if to_player.length_squared() == 0:
                return True
            if self.facing.dot(to_player.normalize()) < _SIGHT_COS:
                return False
            return _line_clear(
                self.pos.x, self.pos.y,
                player.pos.x, player.pos.y,
                solid_regions,
            )

        dist_sq = (player.pos - self.pos).length_squared()
        if dist_sq > self.alert_radius ** 2:
            return False

        return True

    # =====================================================
    # DAMAGE
    # =====================================================

    def take_damage(self, amount, source_position, knockback=0):
        self.health -= amount
        self.flash_timer = self.flash_duration

        effective_kb = max(0, knockback - self.knockback_resistance)
        if effective_kb > 0:
            direction = self.pos - source_position
            if direction.length_squared() > 0:
                direction = direction.normalize()
                self.vel = direction * effective_kb
                self.knockback_timer = 0.2

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen, camera):
        if self.visibility_alpha <= 0:
            return

        draw_color = (255, 255, 255) if self.flash_timer > 0 else self.color

        rect = pygame.Rect(
            0, 0,
            self.size * 2,
            self.size * 2
        )
        rect.center = camera.apply(self.pos)

        alpha = int(self.visibility_alpha)
        if alpha >= 255:
            pygame.draw.rect(screen, draw_color, rect)
        else:
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            surf.fill((*draw_color, alpha))
            screen.blit(surf, rect.topleft)

        # Facing indicator line
        screen_pos = pygame.Vector2(camera.apply(self.pos))
        line_end = screen_pos + self.facing * self.size
        pygame.draw.line(screen, (255, 0, 0), screen_pos, line_end, 2)


def _line_clear(x1, y1, x2, y2, regions):
    """True if no solid region blocks the line segment (Liang-Barsky)."""
    dx = x2 - x1
    dy = y2 - y1
    for region in regions:
        r = region.rect
        t_min, t_max = 0.0, 1.0
        clipped = True
        for edge_p, edge_q in [(-dx, x1 - r.left),
                                (dx, r.right - x1),
                                (-dy, y1 - r.top),
                                (dy, r.bottom - y1)]:
            if edge_p == 0:
                if edge_q < 0:
                    clipped = False
                    break
            else:
                t = edge_q / edge_p
                if edge_p < 0:
                    t_min = max(t_min, t)
                else:
                    t_max = min(t_max, t)
                if t_min > t_max:
                    clipped = False
                    break
        if clipped and t_min <= t_max:
            return False
    return True
