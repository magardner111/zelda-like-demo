import pygame
import sys

from settings import WIDTH, HEIGHT, FPS, BACKGROUND_COLOR

from core.camera import Camera
from core.input_manager import InputManager
from core.player_base import Player

from maps import Lvl1Map

from weapons.sword import Sword
from data.player_stats import PLAYER_STATS
from data.sword_stats import SWORD_STATS


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pattern Sandbox")

    clock = pygame.time.Clock()

    camera = Camera()
    input_manager = InputManager()

    # -----------------------------
    # Create Player
    # -----------------------------
    player = Player(
        position=(WIDTH // 2, HEIGHT // 2),
        stats=PLAYER_STATS
    )

    # Attach sword
    player.add_weapon(
        "sword",
        Sword(player, SWORD_STATS["basic"])
    )

    # -----------------------------
    # Load Map
    # -----------------------------
    current_map = Lvl1Map()

    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        # -----------------------------
        # Events
        # -----------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # -----------------------------
        # Input
        # -----------------------------
        input_manager.update()

        # -----------------------------
        # Update
        # -----------------------------
        current_map.update(dt, player)
        player.update(dt, input_manager, current_map.enemies)
        camera.update(dt)

        # -----------------------------
        # Draw
        # -----------------------------
        screen.fill(BACKGROUND_COLOR)

        current_map.draw(screen, camera)
        player.draw(screen, camera)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
