import json

import pygame

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
                layer.add_wall_region(
                    WallRegion((wr["x"], wr["y"], wr["w"], wr["h"]),
                               REGION_STATS["wall"])
                )
            for fr in layer_data["floor_regions"]:
                rtype = fr["type"]
                rect = (fr["x"], fr["y"], fr["w"], fr["h"])
                if rtype in _LIQUID_TYPES:
                    region = LiquidRegion(rect, rtype, REGION_STATS[rtype])
                elif rtype in _OBJECT_TYPES:
                    region = ObjectRegion(rect, rtype, REGION_STATS[rtype])
                else:
                    region = FloorRegion(rect, rtype, REGION_STATS[rtype])
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
        for enemy in self.enemies:
            layer = self.get_layer(enemy.current_layer)
            solid_regions = layer.get_solid_regions() if layer else []

            enemy.update(dt, player, solid_regions)

            resolve_entity_vs_regions(enemy, solid_regions)

            self.clamp_entity(enemy)

            self.check_stairway_transitions(enemy)

            self.check_fall(enemy)

        self.enemies = [e for e in self.enemies if e.health > 0]

    def check_fall(self, entity):
        """If entity is on a layer with no floor beneath, drop to the next layer below."""
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
        entity.current_layer = best.elevation if best else 0

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
                region.draw(screen, camera)

        # Darken lower layers where the current layer has no regions
        if view_layer > 0:
            map_rect = pygame.Rect(0, 0, self.width, self.height)
            screen_rect = map_rect.move(camera.offset)
            dark = pygame.Surface((screen_rect.width, screen_rect.height), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 100))
            screen.blit(dark, screen_rect.topleft)

        # Draw current layer's floor regions on top at full brightness
        if current_layer:
            for region in current_layer.floor_regions:
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
        """Draw wall regions on top of entities for all layers up to view_layer."""
        layers_below = sorted(
            [l for l in self.floor_layers if l.elevation <= view_layer],
            key=lambda l: l.elevation,
        )
        for layer in layers_below:
            for region in layer.wall_regions:
                region.draw(screen, camera)
