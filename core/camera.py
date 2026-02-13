import pygame
import random

from settings import WIDTH, HEIGHT


class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)
        self.target = None
        self.map_bounds = None  # (map_width, map_height)

        # Shake
        self.shake_timer = 0.0
        self.shake_duration = 0.6
        self.shake_strength = 12

    # -------------------------
    # Public API
    # -------------------------

    def follow(self, target):
        """Set the target to follow. Target must have a .pos attribute."""
        self.target = target

    def set_bounds(self, map_width, map_height):
        """Set map bounds for camera clamping."""
        self.map_bounds = (map_width, map_height)

    def shake(self, duration=None, strength=None):
        """
        Trigger screen shake.
        """
        if duration is not None:
            self.shake_duration = duration
        if strength is not None:
            self.shake_strength = strength

        self.shake_timer = self.shake_duration

    def update(self, dt):
        """
        Update camera each frame.
        """
        # Center on target
        if self.target:
            self.offset.x = WIDTH / 2 - self.target.pos.x
            self.offset.y = HEIGHT / 2 - self.target.pos.y
        else:
            self.offset.update(0, 0)

        # Clamp to map bounds
        if self.map_bounds:
            map_w, map_h = self.map_bounds

            # If map is smaller than viewport, center the map on screen
            if map_w <= WIDTH:
                self.offset.x = (WIDTH - map_w) / 2
            else:
                # Don't let left edge of map go past left edge of screen
                self.offset.x = min(self.offset.x, 0)
                # Don't let right edge of map go past right edge of screen
                self.offset.x = max(self.offset.x, WIDTH - map_w)

            if map_h <= HEIGHT:
                self.offset.y = (HEIGHT - map_h) / 2
            else:
                self.offset.y = min(self.offset.y, 0)
                self.offset.y = max(self.offset.y, HEIGHT - map_h)

        # Apply shake on top
        if self.shake_timer > 0:
            self.shake_timer -= dt

            intensity = (
                self.shake_timer / self.shake_duration
            ) * self.shake_strength

            self.offset.x += random.uniform(-intensity, intensity)
            self.offset.y += random.uniform(-intensity, intensity)

    def apply(self, position):
        """
        Apply camera offset to a world position.
        """
        return position + self.offset
