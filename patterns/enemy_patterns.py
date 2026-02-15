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
