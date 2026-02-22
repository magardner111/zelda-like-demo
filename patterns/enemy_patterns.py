import pygame


# =====================================================
# BASE PATTERN (Optional but useful)
# =====================================================

class PatternBase:
    def update(self, enemy, dt):
        raise NotImplementedError


# =====================================================
# UP / DOWN PATTERN
# =====================================================

class UpDownPattern(PatternBase):
    def __init__(self, distance=30, pause_time=2.0, speed=60):
        """
        distance: how far to move up/down (pixels)
        pause_time: how long to pause at each end
        speed: movement speed (pixels per second)
        """
        self.distance = distance
        self.pause_time = pause_time
        self.speed = speed

        self.state = "moving_up"
        self.start_pos = None
        self.pause_timer = 0.0

    def update(self, enemy, dt):
        if self.start_pos is None:
            self.start_pos = pygame.Vector2(enemy.pos)

        if self.state == "moving_up":
            enemy.facing = pygame.Vector2(0, -1)
            enemy.pos.y -= self.speed * dt

            if enemy.pos.y <= self.start_pos.y - self.distance:
                enemy.pos.y = self.start_pos.y - self.distance
                self.state = "pause_top"
                self.pause_timer = self.pause_time

        elif self.state == "pause_top":
            self.pause_timer -= dt
            if self.pause_timer <= 0:
                self.state = "moving_down"

        elif self.state == "moving_down":
            enemy.facing = pygame.Vector2(0, 1)
            enemy.pos.y += self.speed * dt

            if enemy.pos.y >= self.start_pos.y:
                enemy.pos.y = self.start_pos.y
                self.state = "pause_bottom"
                self.pause_timer = self.pause_time

        elif self.state == "pause_bottom":
            self.pause_timer -= dt
            if self.pause_timer <= 0:
                self.state = "moving_up"


# =====================================================
# KEEP DISTANCE PATTERN
# =====================================================

class KeepDistancePattern(PatternBase):
    """Follow the player while maintaining a minimum distance.

    The enemy orbits when already in the sweet spot, retreats when too close,
    and closes in when too far.  Set ``pattern.player`` each frame before
    calling ``update()``.

    Parameters
    ----------
    min_dist : float
        Minimum pixels to keep between enemy and player.
    max_dist : float
        Maximum pixels before the enemy moves in closer.
    speed : float
        Movement speed in pixels per second.
    """

    def __init__(self, min_dist=200, max_dist=350, speed=250):
        self.min_dist = min_dist
        self.max_dist = max_dist
        self.speed = speed
        self.player = None
        self.line_of_sight = True  # set each frame by the owning enemy

        self._orbit_dir = 1        # +1 or -1 — orbit handedness
        self._orbit_timer = 0.0
        self._orbit_switch = 2.0   # seconds between orbit direction flips

    def update(self, enemy, dt):
        if self.player is None:
            return

        to_player = self.player.pos - enemy.pos
        dist = to_player.length()
        if dist < 1.0:
            return

        direction = to_player / dist  # unit vector toward player
        enemy.facing = pygame.Vector2(direction)

        if dist < self.min_dist:
            # Too close — back away
            enemy.pos -= direction * self.speed * dt

        elif dist > self.max_dist or not self.line_of_sight:
            # Move directly toward player; collision system pushes us along walls.
            enemy.pos += direction * self.speed * dt

            # When a wall blocks line of sight, also apply lateral correction so
            # the enemy slides along the wall toward the doorway gap rather than
            # pressing straight into the wall and oscillating.
            # The doorways are centered in walls, so aligning laterally with the
            # player's position aligns us with the gap.
            if not self.line_of_sight:
                if abs(to_player.x) >= abs(to_player.y):
                    # Moving mostly left/right → wall is vertical → align on Y
                    lat = self.player.pos.y - enemy.pos.y
                    if abs(lat) > 1.0:
                        enemy.pos.y += (1.0 if lat > 0 else -1.0) * self.speed * 0.6 * dt
                else:
                    # Moving mostly up/down → wall is horizontal → align on X
                    lat = self.player.pos.x - enemy.pos.x
                    if abs(lat) > 1.0:
                        enemy.pos.x += (1.0 if lat > 0 else -1.0) * self.speed * 0.6 * dt

        else:
            # Sweet spot with clear line of sight — orbit perpendicular.
            # Reduced speed (0.25x) limits lateral drift so the enemy stays
            # roughly aligned with doorways when the player steps through one.
            self._orbit_timer += dt
            if self._orbit_timer >= self._orbit_switch:
                self._orbit_dir *= -1
                self._orbit_timer = 0.0

            perp = pygame.Vector2(-direction.y, direction.x) * self._orbit_dir
            enemy.pos += perp * self.speed * 0.25 * dt


# =====================================================
# KAMIKAZE PATTERN
# =====================================================

class KamikazePattern(PatternBase):
    """Charge directly at the player at full speed with no distance check.

    Explosion parameters are stored here so the owning enemy can read
    them when it creates an ``Explosion`` on contact.

    Parameters
    ----------
    speed : float
        Movement speed in pixels per second.
    explode_radius : float
        Damage radius forwarded to ``Explosion``.
    explode_damage : int
        Damage forwarded to ``Explosion``.
    explode_shake : tuple | None
        ``(duration, intensity)`` forwarded to ``Explosion``.
    """

    def __init__(self, speed=500, explode_radius=80, explode_damage=3,
                 explode_shake=(0.25, 20)):
        self.speed = speed
        self.explode_radius = explode_radius
        self.explode_damage = explode_damage
        self.explode_shake = explode_shake
        self.player = None
        self.line_of_sight = True  # set each frame by the owning enemy (unused here)

    def update(self, enemy, dt):
        if self.player is None:
            return
        to_player = self.player.pos - enemy.pos
        dist = to_player.length()
        if dist < 1.0:
            return
        direction = to_player / dist
        enemy.facing = pygame.Vector2(direction)
        enemy.pos += direction * self.speed * dt
