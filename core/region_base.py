import io
import os
import zipfile

import pygame


class MapRegion:
    _tile_image_cache = {}  # filepath -> pygame.Surface

    # Class-level animation state (shared across all regions)
    _anim_frame_index = 0
    _anim_timer = 0.0
    ANIM_INTERVAL = 0.15  # seconds between frames

    def __init__(self, rect, region_type, color, solid):
        self.rect = pygame.Rect(rect)
        self.region_type = region_type
        self.color = color
        self.solid = solid
        self.tiles_surface = None
        self._animated_tiles = []  # [(local_x, local_y, [surf0, surf1, ...]), ...]

    @classmethod
    def tick_animation(cls, dt):
        """Advance the shared animation timer."""
        cls._anim_timer += dt
        if cls._anim_timer >= cls.ANIM_INTERVAL:
            cls._anim_frame_index += 1
            cls._anim_timer -= cls.ANIM_INTERVAL

    def overlaps_circle(self, pos, radius):
        """Circle-vs-rect overlap test."""
        closest_x = max(self.rect.left, min(pos.x, self.rect.right))
        closest_y = max(self.rect.top, min(pos.y, self.rect.bottom))
        dist_sq = (pos.x - closest_x) ** 2 + (pos.y - closest_y) ** 2
        return dist_sq < radius ** 2

    @staticmethod
    def _load_atile_frames(filepath):
        """Load all numbered PNG frames from a .atile zip archive."""
        frames = []
        with zipfile.ZipFile(filepath, "r") as zf:
            names = sorted(
                (n for n in zf.namelist() if n.endswith(".png")),
                key=lambda n: int(os.path.splitext(os.path.basename(n))[0]),
            )
            for name in names:
                data = zf.read(name)
                surf = pygame.image.load(io.BytesIO(data), name).convert_alpha()
                frames.append(surf)
        return frames

    def load_tiles(self, tiles_dict, region_type):
        """Pre-render tile images onto a surface.

        tiles_dict: {"x,y": "filename.png", ...} (map-space coords)
        region_type: subdirectory under assets/tiles/ (e.g. "grass", "wall")
        """
        tile_dir = os.path.join(
            os.path.dirname(__file__), "..", "assets", "tiles", region_type
        )
        surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self._animated_tiles = []
        for key, filename in tiles_dict.items():
            tx, ty = (int(v) for v in key.split(","))
            local_x = tx - self.rect.x
            local_y = ty - self.rect.y
            filepath = os.path.join(tile_dir, filename)

            if filename.lower().endswith(".atile"):
                # Animated tile — load frames, don't blit onto static surface
                cached = MapRegion._tile_image_cache.get(filepath)
                if cached is None:
                    cached = self._load_atile_frames(filepath)
                    MapRegion._tile_image_cache[filepath] = cached
                if cached:
                    self._animated_tiles.append((local_x, local_y, cached))
            else:
                # Static tile
                img = MapRegion._tile_image_cache.get(filepath)
                if img is None:
                    img = pygame.image.load(filepath).convert_alpha()
                    MapRegion._tile_image_cache[filepath] = img
                surf.blit(img, (local_x, local_y))
        self.tiles_surface = surf

    def draw(self, screen, camera):
        screen_rect = self.rect.move(camera.offset)
        if self.tiles_surface:
            screen.blit(self.tiles_surface, screen_rect.topleft)
        else:
            pygame.draw.rect(screen, self.color, screen_rect)
        # Draw animated tile frames on top
        if self._animated_tiles:
            ox, oy = screen_rect.topleft
            idx = MapRegion._anim_frame_index
            for local_x, local_y, frames in self._animated_tiles:
                frame = frames[idx % len(frames)]
                screen.blit(frame, (ox + local_x, oy + local_y))


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
