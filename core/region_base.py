import os

import pygame


class MapRegion:
    _tile_image_cache = {}  # filepath -> pygame.Surface

    def __init__(self, rect, region_type, color, solid):
        self.rect = pygame.Rect(rect)
        self.region_type = region_type
        self.color = color
        self.solid = solid
        self.tiles_surface = None

    def overlaps_circle(self, pos, radius):
        """Circle-vs-rect overlap test."""
        closest_x = max(self.rect.left, min(pos.x, self.rect.right))
        closest_y = max(self.rect.top, min(pos.y, self.rect.bottom))
        dist_sq = (pos.x - closest_x) ** 2 + (pos.y - closest_y) ** 2
        return dist_sq < radius ** 2

    def load_tiles(self, tiles_dict, region_type):
        """Pre-render tile images onto a surface.

        tiles_dict: {"x,y": "filename.png", ...} (map-space coords)
        region_type: subdirectory under assets/tiles/ (e.g. "grass", "wall")
        """
        tile_dir = os.path.join(
            os.path.dirname(__file__), "..", "assets", "tiles", region_type
        )
        surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        for key, filename in tiles_dict.items():
            tx, ty = (int(v) for v in key.split(","))
            filepath = os.path.join(tile_dir, filename)
            img = MapRegion._tile_image_cache.get(filepath)
            if img is None:
                img = pygame.image.load(filepath).convert_alpha()
                MapRegion._tile_image_cache[filepath] = img
            surf.blit(img, (tx - self.rect.x, ty - self.rect.y))
        self.tiles_surface = surf

    def draw(self, screen, camera):
        screen_rect = self.rect.move(camera.offset)
        if self.tiles_surface:
            screen.blit(self.tiles_surface, screen_rect.topleft)
        else:
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
