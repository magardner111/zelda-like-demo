import pygame

ROCK_SPEED = 140
ROCK_RADIUS = 5
ROCK_COLOR = (140, 120, 90)
SHRINK_DURATION = 0.25
PLAYER_RADIUS = 14  # overshoot distance past the player


class Rock:
    """A small thrown rock that flies in a straight line, overshoots the
    target distance, then shrinks away and disappears."""

    def __init__(self, pos, direction, target_dist, layer, damage=1):
        self.pos = pygame.Vector2(pos)
        self.vel = direction * ROCK_SPEED
        self.target_dist = target_dist + PLAYER_RADIUS
        self.traveled = 0.0
        self.damage = damage
        self.layer = layer
        self.radius = ROCK_RADIUS
        self.done = False
        self._shrinking = False
        self._shrink_timer = 0.0

    def update(self, dt, player):
        if self.done:
            return

        if self._shrinking:
            self._shrink_timer += dt
            t = self._shrink_timer / SHRINK_DURATION
            self.radius = max(0, ROCK_RADIUS * (1.0 - t))
            if t >= 1.0:
                self.done = True
            return

        # Fly forward
        step = self.vel * dt
        self.pos += step
        self.traveled += step.length()

        # Player collision (circle vs circle, same layer only)
        if player.current_layer == self.layer:
            dist_sq = (player.pos - self.pos).length_squared()
            if dist_sq <= (player.radius + self.radius) ** 2:
                player.take_damage(self.damage, self.pos, knockback=150)
                self.done = True
                return

        # Begin shrinking after overshooting past the player
        if self.traveled >= self.target_dist:
            self._shrinking = True

    def draw(self, screen, camera):
        if self.done or self.radius < 1:
            return
        screen_pos = camera.apply(self.pos)
        pygame.draw.circle(screen, ROCK_COLOR, (int(screen_pos.x), int(screen_pos.y)),
                           max(1, int(self.radius)))
