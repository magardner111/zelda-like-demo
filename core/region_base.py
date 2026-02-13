import pygame


class MapRegion:
    def __init__(self, rect, region_type, color, solid):
        self.rect = pygame.Rect(rect)
        self.region_type = region_type
        self.color = color
        self.solid = solid

    def overlaps_circle(self, pos, radius):
        """Circle-vs-rect overlap test."""
        closest_x = max(self.rect.left, min(pos.x, self.rect.right))
        closest_y = max(self.rect.top, min(pos.y, self.rect.bottom))
        dist_sq = (pos.x - closest_x) ** 2 + (pos.y - closest_y) ** 2
        return dist_sq < radius ** 2

    def draw(self, screen, camera):
        screen_rect = self.rect.move(camera.offset)
        pygame.draw.rect(screen, self.color, screen_rect)


class WallRegion(MapRegion):
    def __init__(self, rect, stats):
        super().__init__(rect, "wall", stats["color"], solid=True)


class FloorRegion(MapRegion):
    def __init__(self, rect, region_type, stats):
        super().__init__(rect, region_type, stats["color"], solid=False)


class LiquidRegion(MapRegion):
    def __init__(self, rect, region_type, stats):
        super().__init__(rect, region_type, stats["color"], solid=False)
        self.speed_factor = stats.get("speed_factor", 1.0)
        self.damage_per_sec = stats.get("damage_per_sec", 0)

    def apply_effects(self, entity, dt):
        if self.damage_per_sec > 0:
            entity.health -= self.damage_per_sec * dt


class ObjectRegion(MapRegion):
    def __init__(self, rect, region_type, stats):
        super().__init__(rect, region_type, stats["color"], solid=True)
        self.interactable = stats.get("interactable", False)
