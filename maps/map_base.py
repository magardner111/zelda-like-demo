import pygame


class MapBase:
    def __init__(self, width, height, bg_color=(30, 34, 42)):
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.enemies = []

    def clamp_entity(self, entity):
        """Clamp an entity (must have .pos and .radius) within map bounds."""
        r = getattr(entity, "radius", 0)
        entity.pos.x = max(r, min(self.width - r, entity.pos.x))
        entity.pos.y = max(r, min(self.height - r, entity.pos.y))

    def update(self, dt, player):
        for enemy in self.enemies:
            enemy.update(dt, player)
        self.enemies = [e for e in self.enemies if e.health > 0]

    def draw(self, screen, camera):
        # Draw map background
        map_rect = pygame.Rect(0, 0, self.width, self.height)
        screen_rect = map_rect.move(camera.offset)
        pygame.draw.rect(screen, self.bg_color, screen_rect)

        for enemy in self.enemies:
            enemy.draw(screen, camera)
