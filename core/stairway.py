import pygame


class Stairway:
    def __init__(self, rect, from_layer, to_layer, color=(200, 180, 100)):
        self.rect = pygame.Rect(rect)
        self.from_layer = from_layer
        self.to_layer = to_layer
        self.color = color
        self._occupied = set()  # entity ids currently inside the stairway

    def _overlaps(self, entity):
        r = getattr(entity, "radius", 0)
        closest_x = max(self.rect.left, min(entity.pos.x, self.rect.right))
        closest_y = max(self.rect.top, min(entity.pos.y, self.rect.bottom))
        dist_sq = (entity.pos.x - closest_x) ** 2 + (entity.pos.y - closest_y) ** 2
        return dist_sq < r ** 2

    def check_transition(self, entity):
        """Returns target layer on first overlap, None while still inside or outside."""
        eid = id(entity)
        overlapping = self._overlaps(entity)

        if not overlapping:
            self._occupied.discard(eid)
            return None

        # Already inside — no repeated transitions
        if eid in self._occupied:
            return None

        # First frame of overlap — transition and mark occupied
        self._occupied.add(eid)
        if entity.current_layer == self.from_layer:
            return self.to_layer
        elif entity.current_layer == self.to_layer:
            return self.from_layer
        return None

    def draw(self, screen, camera, current_layer):
        if current_layer == self.from_layer or current_layer == self.to_layer:
            screen_rect = self.rect.move(camera.offset)
            pygame.draw.rect(screen, self.color, screen_rect)
