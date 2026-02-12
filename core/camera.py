import pygame
import random


class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)

        # Shake
        self.shake_timer = 0.0
        self.shake_duration = 0.6
        self.shake_strength = 12

    # -------------------------
    # Public API
    # -------------------------

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
        self.offset.update(0, 0)

        if self.shake_timer > 0:
            self.shake_timer -= dt

            intensity = (
                self.shake_timer / self.shake_duration
            ) * self.shake_strength

            self.offset.x = random.uniform(-intensity, intensity)
            self.offset.y = random.uniform(-intensity, intensity)

    def apply(self, position):
        """
        Apply camera offset to a world position.
        """
        return position + self.offset
