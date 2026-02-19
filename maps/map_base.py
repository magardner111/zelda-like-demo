import json
import math

import pygame

from settings import EDGE_SLIDE_THRESHOLD, EDGE_SLIDE_ACCEL, EDGE_SLIDE_MAX_SPEED

_PI_OVER_4 = math.pi / 4
_SLIDE_SAMPLE_DIRS = [
    (math.cos(i * _PI_OVER_4), math.sin(i * _PI_OVER_4)) for i in range(8)
]

# Enemies beyond this distance from the player skip full AI updates each frame.
# ~2x the screen diagonal (960x800 → diagonal ≈ 1250px).
_ENEMY_CULL_DIST_SQ = 2500 ** 2

from core.collision import resolve_entity_vs_regions
from core.enemy_base import Enemy
from core.floor_layer import FloorLayer
from core.region_base import FloorRegion, LiquidRegion, ObjectRegion, WallRegion
from core.stairway import Stairway, StairDirection
from core.region_base import ObjectRegion as _ObjectRegion
from core.visibility import compute_visibility_polygon, point_in_polygon
from data.enemy_stats import ENEMY_STATS
from data.pattern_registry import PATTERN_REGISTRY, get_pattern_class
from data.region_stats import REGION_STATS

# Region type -> class mapping (matches editor categories)
_LIQUID_TYPES = {"water", "lava"}
_OBJECT_TYPES = {"chest"}


class MapBase:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.enemies = []
        self.floor_layers = []
        self.stairways = []
        self._visibility_poly = None

    @classmethod
    def from_json(cls, path):
        """Construct a MapBase from a JSON file (editor format)."""
        with open(path, "r") as f:
            data = json.load(f)

        map_obj = cls(width=data["width"], height=data["height"])

        for layer_data in data["layers"]:
            layer = FloorLayer(
                elevation=layer_data["elevation"],
                bg_color=tuple(layer_data["bg_color"]),
            )
            for wr in layer_data["wall_regions"]:
                region = WallRegion((wr["x"], wr["y"], wr["w"], wr["h"]),
                                    REGION_STATS["wall"])
                if wr.get("tiles"):
                    region.load_tiles(wr["tiles"], "wall")
                layer.add_wall_region(region)
            for fr in layer_data["floor_regions"]:
                rtype = fr["type"]
                rect = (fr["x"], fr["y"], fr["w"], fr["h"])
                if rtype in _LIQUID_TYPES:
                    region = LiquidRegion(rect, rtype, REGION_STATS[rtype])
                elif rtype in _OBJECT_TYPES:
                    region = ObjectRegion(rect, rtype, REGION_STATS[rtype])
                else:
                    region = FloorRegion(rect, rtype, REGION_STATS[rtype])
                if fr.get("tiles"):
                    region.load_tiles(fr["tiles"], rtype)
                layer.add_floor_region(region)
            map_obj.add_layer(layer)

        # Load stairways — support both per-layer and legacy top-level format
        all_stairways = list(data.get("stairways", []))
        for layer_data in data["layers"]:
            all_stairways.extend(layer_data.get("stairways", []))
        for sw in all_stairways:
            map_obj.add_stairway(
                Stairway(
                    (sw["x"], sw["y"], sw["w"], sw["h"]),
                    from_layer=sw["from_layer"],
                    to_layer=sw["to_layer"],
                    direction=StairDirection(sw.get("direction", "left")),
                )
            )

        # Load enemies
        for layer_data in data["layers"]:
            for edata in layer_data.get("enemies", []):
                etype = edata["type"]
                stats = ENEMY_STATS.get(etype)
                if stats is None:
                    continue
                enemy = Enemy((edata["x"], edata["y"]), stats)
                enemy.current_layer = layer_data["elevation"]
                facing_str = edata.get("facing", "down")
                facing_map = {"down": (0, 1), "up": (0, -1),
                              "left": (-1, 0), "right": (1, 0)}
                fx, fy = facing_map.get(facing_str, (0, 1))
                enemy.facing = pygame.Vector2(fx, fy)
                pdata = edata.get("pattern")
                if pdata and pdata.get("type") in PATTERN_REGISTRY:
                    pcls = get_pattern_class(pdata["type"])
                    # Build params: use registry defaults, overridden by JSON values
                    defaults = PATTERN_REGISTRY[pdata["type"]]["params"]
                    params = dict(defaults)
                    for k, v in pdata.items():
                        if k != "type":
                            params[k] = v
                    enemy.pattern = pcls(**params)
                map_obj.enemies.append(enemy)

        return map_obj

    def add_layer(self, layer):
        self.floor_layers.append(layer)

    def add_stairway(self, stairway):
        self.stairways.append(stairway)

    def get_layer(self, elevation):
        for layer in self.floor_layers:
            if layer.elevation == elevation:
                return layer
        return None

    def clamp_entity(self, entity):
        """Clamp an entity (must have .pos and .radius) within map bounds."""
        r = getattr(entity, "radius", 0)
        entity.pos.x = max(r, min(self.width - r, entity.pos.x))
        entity.pos.y = max(r, min(self.height - r, entity.pos.y))

    def update(self, dt, player):
        # Cache layers to avoid O(layers) lookup per enemy
        layer_cache = {}

        for enemy in self.enemies:
            elev = enemy.current_layer
            if elev not in layer_cache:
                layer_cache[elev] = self.get_layer(elev)
            layer = layer_cache[elev]
            solid_regions = layer.get_solid_regions() if layer else []

            # Skip full AI update for enemies far off-screen (they'll resume when nearby)
            dist_sq = (enemy.pos - player.pos).length_squared()
            if dist_sq > _ENEMY_CULL_DIST_SQ:
                continue

            enemy.update(dt, player, solid_regions)

            resolve_entity_vs_regions(enemy, solid_regions)

            self.clamp_entity(enemy)

            self.check_stairway_transitions(enemy)

            self.check_edge_slide(enemy, dt)

            self.check_fall(enemy)

        self.enemies = [e for e in self.enemies if e.health > 0]

    def check_edge_slide(self, entity, dt):
        """Apply LTTP-style edge sliding when entity is partially off a ledge.

        Samples 8 points at radius * EDGE_SLIDE_THRESHOLD from the entity
        center. Any sample point over void means the entity is near a ledge
        and a slide force accelerates them toward the void.
        """
        if getattr(entity, "falling", False):
            return
        layer = self.get_layer(entity.current_layer)
        if layer is None or layer.elevation == 0:
            return
        # Skip if entity is on a stairway
        for stairway in self.stairways:
            if (stairway.from_layer == entity.current_layer or
                    stairway.to_layer == entity.current_layer):
                if stairway._overlaps(entity):
                    return

        r = getattr(entity, "radius", 0)

        # Full circle must still overlap floor; otherwise let check_fall handle
        if not layer.has_floor_at(entity.pos, r):
            return

        # Sample 8 evenly spaced points at test_r from center
        test_r = r * EDGE_SLIDE_THRESHOLD
        slide_dir = pygame.Vector2(0, 0)
        off_count = 0
        ex, ey = entity.pos.x, entity.pos.y
        for dx, dy in _SLIDE_SAMPLE_DIRS:
            if not layer.point_on_floor(ex + test_r * dx, ey + test_r * dy):
                off_count += 1
                slide_dir.x += dx
                slide_dir.y += dy

        if off_count == 0:
            # All sample points on floor → safe
            entity._slide_vel = pygame.Vector2(0, 0)
            return

        if slide_dir.length_squared() > 0:
            slide_dir = slide_dir.normalize()
        else:
            slide_dir = pygame.Vector2(0, 1)

        entity._slide_vel += slide_dir * EDGE_SLIDE_ACCEL * dt
        if entity._slide_vel.length() > EDGE_SLIDE_MAX_SPEED:
            entity._slide_vel = entity._slide_vel.normalize() * EDGE_SLIDE_MAX_SPEED

        entity.pos += entity._slide_vel * dt

    def check_fall(self, entity):
        """If entity is on a layer with no floor beneath, drop to the next layer below."""
        # Don't re-trigger while already falling
        if getattr(entity, "falling", False):
            return
        layer = self.get_layer(entity.current_layer)
        if layer is None or layer.elevation == 0:
            return
        r = getattr(entity, "radius", 0)
        # Stairways count as floor for both connected layers
        if layer.has_floor_at(entity.pos, r):
            return
        for stairway in self.stairways:
            if (stairway.from_layer == entity.current_layer or
                    stairway.to_layer == entity.current_layer):
                if stairway._overlaps(entity):
                    return
        # No floor or stairway — fall to the next layer below
        best = None
        for candidate in self.floor_layers:
            if candidate.elevation < layer.elevation:
                if best is None or candidate.elevation > best.elevation:
                    best = candidate
        target = best.elevation if best else 0
        entity.start_fall(target)

    def check_stairway_transitions(self, entity):
        # After a transition, ignore all stairways until the player steps
        # off every overlapping one (prevents bounce-back from stairs at
        # the same coords on the destination layer).
        if getattr(entity, "_stairway_cooldown", False):
            still_on = any(sw._overlaps(entity) for sw in self.stairways)
            if still_on:
                return
            entity._stairway_cooldown = False

        for stairway in self.stairways:
            result = stairway.check_transition(entity)
            if result is not None:
                entity.current_layer = result
                entity._stairway_cooldown = True
                return

    def update_visibility(self, player):
        """Compute and cache the visibility polygon for the current frame."""
        if not player.limit_view:
            self._visibility_poly = None
            return
        layer = self.get_layer(player.current_layer)
        wall_rects = [r.rect for r in layer.wall_regions] if layer else []
        self._visibility_poly = compute_visibility_polygon(
            (player.pos.x, player.pos.y), wall_rects,
            self.width, self.height,
        )

    def is_visible(self, x, y):
        """Check if a map-space point is inside the cached visibility polygon."""
        if self._visibility_poly is None:
            return True
        return point_in_polygon(x, y, self._visibility_poly)

    def draw(self, screen, camera, view_layer=0):
        """Draw all layers from 0 up to view_layer. Layer 0 fills its bg;
        upper layers only draw their regions so lower layers show through gaps.
        Areas without regions on the current layer are darkened."""
        layers_below = sorted(
            [l for l in self.floor_layers if l.elevation <= view_layer],
            key=lambda l: l.elevation,
        )

        # Viewport in world-space with a small margin to avoid edge popping
        sw, sh = screen.get_size()
        _MARGIN = 64
        viewport = pygame.Rect(
            -camera.offset.x - _MARGIN,
            -camera.offset.y - _MARGIN,
            sw + _MARGIN * 2,
            sh + _MARGIN * 2,
        )

        current_layer = None
        for layer in layers_below:
            # Only the bottom layer fills the entire map background
            if layer.elevation == 0:
                map_rect = pygame.Rect(0, 0, self.width, self.height)
                screen_rect = map_rect.move(camera.offset)
                pygame.draw.rect(screen, layer.bg_color, screen_rect)

            if layer.elevation == view_layer:
                current_layer = layer
                continue

            for region in layer.floor_regions:
                if viewport.colliderect(region.rect):
                    region.draw(screen, camera)
            for region in layer.wall_regions:
                if viewport.colliderect(region.rect):
                    region.draw(screen, camera)

        # Darken lower layers where the current layer has no regions.
        # Use a screen-sized surface — NOT map-sized — to avoid allocating a
        # potentially enormous surface each frame on large maps.
        if view_layer > 0:
            dark = pygame.Surface((sw, sh), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 100))
            screen.blit(dark, (0, 0))

        # Draw current layer's floor regions on top at full brightness
        if current_layer:
            for region in current_layer.floor_regions:
                if not viewport.colliderect(region.rect):
                    continue
                if isinstance(region, _ObjectRegion) and \
                        not self.is_visible(region.rect.centerx, region.rect.centery):
                    continue
                region.draw(screen, camera)

        # Draw stairways visible on the current layer
        for stairway in self.stairways:
            stairway.draw(screen, camera, view_layer)

    def draw_visibility(self, screen, camera, player):
        """Draw a dark overlay everywhere the player can't see."""
        if self._visibility_poly is None or len(self._visibility_poly) < 3:
            return

        # Convert from map coords to screen coords
        ox, oy = camera.offset
        screen_poly = [(x + ox, y + oy) for x, y in self._visibility_poly]

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        # Punch out the visible area by drawing transparent polygon
        pygame.draw.polygon(overlay, (0, 0, 0, 0), screen_poly)
        screen.blit(overlay, (0, 0))

    def draw_walls(self, screen, camera, view_layer=0):
        """Draw wall regions on top of entities for the current layer only.
        Lower-layer walls are drawn during draw() so they sit beneath
        the current layer's floor and get the darkening overlay."""
        sw, sh = screen.get_size()
        viewport = pygame.Rect(-camera.offset.x - 64, -camera.offset.y - 64,
                               sw + 128, sh + 128)
        for layer in self.floor_layers:
            if layer.elevation == view_layer:
                for region in layer.wall_regions:
                    if viewport.colliderect(region.rect):
                        region.draw(screen, camera)
                break
