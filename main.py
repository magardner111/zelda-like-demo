import pygame
import sys

from settings import WIDTH, HEIGHT, FPS, BACKGROUND_COLOR

from core.camera import Camera
from core.collision import (
    check_player_enemy_collisions,
    resolve_entity_vs_regions,
    apply_region_effects,
)
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
            current_map.draw(screen, camera, player.current_layer)
            player.draw(screen, camera)
            current_map.draw_walls(screen, camera, player.current_layer)
            hud.draw(screen)
            menu.draw(screen)
        else:
            # -----------------------------
            # Update
            # -----------------------------
            current_map.update(dt, player)

            # Get regions for player's current layer
            layer = current_map.get_layer(player.current_layer)
            solid_regions = layer.get_solid_regions() if layer else []
            effect_regions = layer.get_effect_regions() if layer else []

            # Apply liquid/effect regions
            speed_factor = apply_region_effects(player, effect_regions, dt)

            # Filter enemies to same layer
            enemies_on_layer = [
                e for e in current_map.enemies
                if e.current_layer == player.current_layer
            ]

            player.update(dt, input_manager, enemies_on_layer, camera, speed_factor)

            # Wall collision
            resolve_entity_vs_regions(player, solid_regions)

            current_map.clamp_entity(player)

            # Stairway transitions
            current_map.check_stairway_transitions(player)

            # Fall off upper layers if no floor beneath
            current_map.check_fall(player)

            # Enemy-player collision (same layer only)
            check_player_enemy_collisions(player, enemies_on_layer)

            camera.update(dt)

            # -----------------------------
            # Draw
            # -----------------------------
            screen.fill(BACKGROUND_COLOR)
            current_map.draw(screen, camera, player.current_layer)

            # Draw enemies on current layer
            for enemy in current_map.enemies:
                if enemy.current_layer == player.current_layer:
                    enemy.draw(screen, camera)

            player.draw(screen, camera)
            current_map.draw_walls(screen, camera, player.current_layer)
            hud.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
