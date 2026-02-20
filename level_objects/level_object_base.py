import pygame


class LevelObject:
    """Base class for interactable non-actor objects like doors, chests, switches."""

    def __init__(self, position, size):
        self.pos = pygame.Vector2(position)
        self.size = size  # (width, height) tuple
        self.rect = pygame.Rect(
            self.pos.x - size[0] // 2,
            self.pos.y - size[1] // 2,
            size[0],
            size[1]
        )
        self.solid = True  # Whether this object blocks entities
        self.active = True  # Whether this object is active in the world

    def overlaps_circle(self, pos, radius):
        """Circle-vs-rect overlap test (same as MapRegion)."""
        # Use rotated rect if object provides one (e.g., doors)
        check_rect = self.get_collision_rect() if hasattr(self, 'get_collision_rect') else self.rect

        closest_x = max(check_rect.left, min(pos.x, check_rect.right))
        closest_y = max(check_rect.top, min(pos.y, check_rect.bottom))
        dist_sq = (pos.x - closest_x) ** 2 + (pos.y - closest_y) ** 2
        return dist_sq < radius ** 2

    def on_player_touch(self, player):
        """Called when the player touches this object. Override in subclasses."""
        pass

    def update(self, dt):
        """Update object state. Override in subclasses."""
        pass

    def draw(self, screen, camera):
        """Draw the object. Override in subclasses."""
        pass
