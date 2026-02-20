import argparse
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

from core.game_options import GameOptions
from core.region_base import MapRegion
from maps.map_base import MapBase
from maps import generate_layout, generate_map
from menus import MainMenu
from hud import GameHud

from weapons.sword import Sword
from data.player_stats import PLAYER_STATS
from data.sword_stats import SWORD_STATS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", type=str, default=None,
                        help="Path to JSON map file")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for procedural map generation")
    args = parser.parse_args()

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
    if args.map:
        current_map = MapBase.from_json(args.map)
    else:
        layout = generate_layout(seed=args.seed)
        current_map, player_start = generate_map(layout)
        player.pos = pygame.Vector2(player_start)
        print(f"Generated map  seed={layout.seed}")
        # Mark starting room as visited
        current_map.mark_current_room_visited(player)
    camera.set_bounds(current_map.width, current_map.height)
    options = GameOptions()
    menu = MainMenu(options=options)
    hud = GameHud(player, options=options, fps_source=clock.get_fps)

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
            MapRegion.tick_animation(dt)
            current_map.update_visibility(player)
            screen.fill(BACKGROUND_COLOR)
            current_map.draw(screen, camera, player.current_layer)
            player.draw(screen, camera)
            current_map.draw_walls(screen, camera, player.current_layer)
            current_map.draw_visibility(screen, camera, player)
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

            # Mark current room as visited for fog of war
            current_map.mark_current_room_visited(player)

            # Drain pending camera shakes from all entities
            for entity in [player] + current_map.enemies:
                if entity._pending_shake is not None:
                    camera.shake(*entity._pending_shake)
                    entity._pending_shake = None

            # Level object interactions (doors, chests, etc.)
            # Check BEFORE collision resolution so player can trigger doors on touch
            current_map.check_level_object_interactions(player)

            # Wall collision — filter to walls near the player so we don't
            # run O(all_walls) checks against the entire map each frame.
            pr = player.radius + 4
            px, py = player.pos.x, player.pos.y
            solid_near = [r for r in solid_regions
                          if r.rect.left - pr < px < r.rect.right + pr
                          and r.rect.top - pr < py < r.rect.bottom + pr]

            # Add solid level objects to collision list
            solid_objects = current_map.get_solid_level_objects()
            all_solid = solid_near + solid_objects

            resolve_entity_vs_regions(player, all_solid)

            current_map.clamp_entity(player)

            # Stairway transitions
            current_map.check_stairway_transitions(player)

            # Edge slide on upper layers
            current_map.check_edge_slide(player, dt)

            # Fall off upper layers if no floor beneath
            current_map.check_fall(player)

            # Enemy-player collision (same layer only)
            check_player_enemy_collisions(player, enemies_on_layer)

            camera.update(dt)

            # -----------------------------
            # Draw
            # -----------------------------
            MapRegion.tick_animation(dt)
            current_map.update_visibility(player)
            screen.fill(BACKGROUND_COLOR)
            current_map.draw(screen, camera, player.current_layer)

            # Fade enemy visibility alpha and draw.
            # Skip enemies that are entirely outside the viewport — no
            # point running point_in_polygon or drawing off-screen enemies.
            _sw, _sh = screen.get_size()
            for enemy in current_map.enemies:
                if enemy.current_layer != player.current_layer:
                    continue
                _ex, _ey = camera.apply(enemy.pos)
                if (_ex + enemy.size < 0 or _ex - enemy.size > _sw or
                        _ey + enemy.size < 0 or _ey - enemy.size > _sh):
                    continue
                if current_map.is_visible(enemy.pos.x, enemy.pos.y):
                    enemy.visibility_alpha = 255
                else:
                    enemy.visibility_alpha = max(0, enemy.visibility_alpha - player.enemy_fade_speed * dt)
                enemy.draw(screen, camera)

            player.draw(screen, camera)
            current_map.draw_walls(screen, camera, player.current_layer)
            current_map.draw_visibility(screen, camera, player)
            hud.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
