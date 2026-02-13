import pygame


class Enemy:
    def __init__(self, position, stats):
        # -----------------------------
        # Position
        # -----------------------------
        self.pos = pygame.Vector2(position)

        # -----------------------------
        # Stats
        # -----------------------------
        self.size = stats["size"]
        self.speed = stats["speed"]
        self.max_health = stats["max_health"]
        self.health = self.max_health
        self.color = stats["color"]

        self.hit_damage = stats.get("hit_damage", 1)

        # -----------------------------
        # Damage Flash
        # -----------------------------
        self.flash_timer = 0.0
        self.flash_duration = 0.1

        # -----------------------------
        # Layer
        # -----------------------------
        self.current_layer = 0

        # -----------------------------
        # Pattern (None for now)
        # -----------------------------
        self.pattern = None

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, dt, player):
        if self.pattern:
            self.pattern.update(self, dt)
    
        if self.flash_timer > 0:
            self.flash_timer -= dt


    # =====================================================
    # DAMAGE
    # =====================================================

    def take_damage(self, amount, source_position):
        self.health -= amount
        self.flash_timer = self.flash_duration

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen, camera):
        draw_color = (255, 255, 255) if self.flash_timer > 0 else self.color

        rect = pygame.Rect(
            0, 0,
            self.size * 2,
            self.size * 2
        )

        rect.center = camera.apply(self.pos)

        pygame.draw.rect(screen, draw_color, rect)
