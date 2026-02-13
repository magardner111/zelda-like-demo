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

    def check_stairway_transitions(self, entity):
        for stairway in self.stairways:
            result = stairway.check_transition(entity)
            if result is not None:
                entity.current_layer = result
                return

    def draw(self, screen, camera, view_layer=0):
        """Draw layer background, floor regions, and stairways."""
        layer = self.get_layer(view_layer)
        if layer:
            # Draw layer background
            map_rect = pygame.Rect(0, 0, self.width, self.height)
            screen_rect = map_rect.move(camera.offset)
            pygame.draw.rect(screen, layer.bg_color, screen_rect)

            # Draw floor regions
            for region in layer.floor_regions:
                region.draw(screen, camera)

        # Draw stairways
        for stairway in self.stairways:
            stairway.draw(screen, camera, view_layer)

    def draw_walls(self, screen, camera, view_layer=0):
        """Draw wall regions on top of entities."""
        layer = self.get_layer(view_layer)
        if layer:
            for region in layer.wall_regions:
                region.draw(screen, camera)
