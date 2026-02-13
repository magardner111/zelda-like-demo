import pygame


class MapBase:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.enemies = []
        self.floor_layers = []
        self.stairways = []

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
            enemy.update(dt, player)
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
        for stairway in self.stairways:
            result = stairway.check_transition(entity)
            if result is not None:
                entity.current_layer = result
                return

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
                region.draw(screen, camera)

        # Draw stairways visible on the current layer
        for stairway in self.stairways:
            stairway.draw(screen, camera, view_layer)

    def draw_walls(self, screen, camera, view_layer=0):
        """Draw wall regions on top of entities for all layers up to view_layer."""
        layers_below = sorted(
            [l for l in self.floor_layers if l.elevation <= view_layer],
            key=lambda l: l.elevation,
        )
        for layer in layers_below:
            for region in layer.wall_regions:
                region.draw(screen, camera)
