import pygame
from enum import Enum


class StairDirection(Enum):
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class Stairway:
    def __init__(self, rect, from_layer, to_layer,
                 direction=StairDirection.LEFT, color=(200, 180, 100)):
        self.rect = pygame.Rect(rect)
        self.from_layer = from_layer
        self.to_layer = to_layer
        self.direction = direction
        self.color = color

    def _overlaps(self, entity):
        r = getattr(entity, "radius", 0)
        closest_x = max(self.rect.left, min(entity.pos.x, self.rect.right))
        closest_y = max(self.rect.top, min(entity.pos.y, self.rect.bottom))
        dist_sq = (entity.pos.x - closest_x) ** 2 + (entity.pos.y - closest_y) ** 2
        return dist_sq < r ** 2

    def _past_midpoint(self, entity):
        """Check if entity has crossed the midpoint in the stair direction."""
        if self.direction == StairDirection.LEFT:
            return entity.pos.x < self.rect.centerx
        elif self.direction == StairDirection.RIGHT:
            return entity.pos.x > self.rect.centerx
        elif self.direction == StairDirection.UP:
            return entity.pos.y < self.rect.centery
        elif self.direction == StairDirection.DOWN:
            return entity.pos.y > self.rect.centery
        return False

    def check_transition(self, entity):
        """Returns target layer when entity crosses the midpoint of the stair
        region in the appropriate direction.  Walking in ``direction`` goes
        from ``from_layer`` to ``to_layer``; walking opposite goes back."""
        if not self._overlaps(entity):
            return None

        past = self._past_midpoint(entity)

        if past and entity.current_layer == self.from_layer:
            return self.to_layer
        elif not past and entity.current_layer == self.to_layer:
            return self.from_layer
        return None

    def draw(self, screen, camera, current_layer):
        if current_layer == self.from_layer or current_layer == self.to_layer:
            screen_rect = self.rect.move(camera.offset)
            pygame.draw.rect(screen, self.color, screen_rect)
