import pygame
import sys

from settings import WIDTH, HEIGHT, FPS, BACKGROUND_COLOR

from core.camera import Camera
from core.collision import check_player_enemy_collisions
from core.input_manager import InputManager
from core.player_base import Player

from maps import Lvl1Map
from menus import MainMenu
from hud import GameHud

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
    camera.follow(player)

    # Attach sword
    player.add_weapon(
        "sword",
        Sword(player, SWORD_STATS["basic"])
    )

    # -----------------------------
    # Load Map
    # -----------------------------
    current_map = Lvl1Map()
    camera.set_bounds(current_map.width, current_map.height)
    menu = MainMenu()
    hud = GameHud(player)

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
        # Menu toggle
        # -----------------------------
        if input_manager.is_pressed("menu"):
            if menu.active:
                menu.close(input_manager)
            else:
                menu.open(input_manager)

        if menu.active:
            menu.update(input_manager)

            # Draw game underneath, then HUD, then menu overlay
            screen.fill(BACKGROUND_COLOR)
            current_map.draw(screen, camera)
            player.draw(screen, camera)
            hud.draw(screen)
            menu.draw(screen)
        else:
            # -----------------------------
            # Update
            # -----------------------------
            current_map.update(dt, player)
            player.update(dt, input_manager, current_map.enemies, camera)
            current_map.clamp_entity(player)
            check_player_enemy_collisions(player, current_map.enemies)
            camera.update(dt)

            # -----------------------------
            # Draw
            # -----------------------------
            screen.fill(BACKGROUND_COLOR)
            current_map.draw(screen, camera)
            player.draw(screen, camera)
            hud.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
