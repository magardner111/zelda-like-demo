import pygame


# =====================================================
# BASE PATTERN (Optional but useful)
# =====================================================

class PatternBase:
    def update(self, enemy, dt, speed_factor=1.0):
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

    def update(self, enemy, dt, speed_factor=1.0):
        if self.start_pos is None:
            self.start_pos = pygame.Vector2(enemy.pos)

        if self.state == "moving_up":
            enemy.facing = pygame.Vector2(0, -1)
            enemy.pos.y -= self.speed * speed_factor * dt

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
            enemy.pos.y += self.speed * speed_factor * dt

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

    def update(self, enemy, dt, speed_factor=1.0):
        if self.player is None:
            return

        to_player = self.player.pos - enemy.pos
        dist = to_player.length()
        if dist < 1.0:
            return

        direction = to_player / dist  # unit vector toward player
        enemy.facing = pygame.Vector2(direction)

        spd = self.speed * speed_factor

        if dist < self.min_dist:
            # Too close — back away
            enemy.pos -= direction * spd * dt

        elif dist > self.max_dist or not self.line_of_sight:
            # Move directly toward player; collision system pushes us along walls.
            enemy.pos += direction * spd * dt

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
                        enemy.pos.y += (1.0 if lat > 0 else -1.0) * spd * 0.6 * dt
                else:
                    # Moving mostly up/down → wall is horizontal → align on X
                    lat = self.player.pos.x - enemy.pos.x
                    if abs(lat) > 1.0:
                        enemy.pos.x += (1.0 if lat > 0 else -1.0) * spd * 0.6 * dt

        else:
            # Sweet spot with clear line of sight — orbit perpendicular.
            # Reduced speed (0.25x) limits lateral drift so the enemy stays
            # roughly aligned with doorways when the player steps through one.
            self._orbit_timer += dt
            if self._orbit_timer >= self._orbit_switch:
                self._orbit_dir *= -1
                self._orbit_timer = 0.0

            perp = pygame.Vector2(-direction.y, direction.x) * self._orbit_dir
            enemy.pos += perp * spd * 0.25 * dt


# =====================================================
# KAMIKAZE PATTERN
# =====================================================

class KamikazePattern(PatternBase):
    """Charge at the player with optional periodic homing corrections.

    On the first update the enemy locks onto the player and commits to
    travelling 110 % of that distance.  If ``homing > 0`` the heading is
    re-locked every ``1 / homing`` seconds, resetting the committed distance
    from the new position.  When the committed distance is exceeded the
    pattern sets ``should_explode = True`` so the owning enemy can detonate
    even on a clean miss.

    Explosion parameters are stored here so the owning enemy can read
    them when it creates an ``Explosion``.

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
    homing : float
        Heading re-locks per second.  ``0`` = straight line after the
        initial lock.  Low values (default 0.15) give only the occasional
        mid-flight correction; high values track the player aggressively.
    """

    def __init__(self, speed=500, explode_radius=80, explode_damage=3,
                 explode_shake=(0.25, 20), homing=0.15):
        self.speed = speed
        self.explode_radius = explode_radius
        self.explode_damage = explode_damage
        self.explode_shake = explode_shake
        self.homing = homing
        self.player = None
        self.line_of_sight = True  # unused; kept for interface consistency

        self._heading = None            # locked unit direction vector
        self._last_adj_pos = None       # enemy pos at last heading lock
        self._committed_dist = 0.0      # 1.1 × dist-to-player at last lock
        self._adj_timer = 0.0
        self._adj_interval = (1.0 / homing) if homing > 0 else float('inf')
        self.should_explode = False     # read by the owning enemy

    def _lock_heading(self, enemy):
        """Re-aim at the player, record position, and reset committed distance."""
        to_player = self.player.pos - enemy.pos
        dist = to_player.length()
        if dist < 1.0:
            self.should_explode = True
            return
        self._heading = to_player / dist
        self._last_adj_pos = pygame.Vector2(enemy.pos)
        self._committed_dist = dist * 1.1
        self._adj_timer = 0.0

    def update(self, enemy, dt, speed_factor=1.0):
        if self.player is None:
            return

        # Initial heading lock on first call
        if self._heading is None:
            self._lock_heading(enemy)
            if self.should_explode:
                return

        # Advance along the locked heading
        enemy.pos += self._heading * self.speed * speed_factor * dt
        enemy.facing = pygame.Vector2(self._heading)

        # Detonate when 110 % of the committed distance is covered
        if (enemy.pos - self._last_adj_pos).length() >= self._committed_dist:
            self.should_explode = True
            return

        # Periodic homing correction
        if self.homing > 0:
            self._adj_timer += dt
            if self._adj_timer >= self._adj_interval:
                self._lock_heading(enemy)
