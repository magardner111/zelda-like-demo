#!/usr/bin/env python3
"""
Simple test script to demonstrate the door system.

Run this to see a door in action. Walk into it to open it.
"""

import pygame
import sys

from settings import WIDTH, HEIGHT, FPS, BACKGROUND_COLOR

from core.camera import Camera
from core.collision import resolve_entity_vs_regions
from core.input_manager import InputManager
from core.player_base import Player

from level_objects.door import Door
from maps.map_base import MapBase
from core.floor_layer import FloorLayer
from core.region_base import FloorRegion, WallRegion
from data.region_stats import REGION_STATS
from data.player_stats import PLAYER_STATS

from weapons.sword import Sword
from data.sword_stats import SWORD_STATS


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Door Test")

    clock = pygame.time.Clock()

    camera = Camera()
    input_manager = InputManager()

    # Create a simple map
    map_obj = MapBase(width=1000, height=1000)
    layer = FloorLayer(elevation=0, bg_color=(30, 30, 35))

    # Add floor
    floor_stats = REGION_STATS["stone"]
    layer.add_floor_region(FloorRegion((0, 0, 1000, 1000), "stone", floor_stats))

    # Add walls
    wall_stats = REGION_STATS["wall"]
    layer.add_wall_region(WallRegion((0, 0, 1000, 20), wall_stats))  # Top
    layer.add_wall_region(WallRegion((0, 980, 1000, 20), wall_stats))  # Bottom
    layer.add_wall_region(WallRegion((0, 0, 20, 1000), wall_stats))  # Left
    layer.add_wall_region(WallRegion((980, 0, 20, 1000), wall_stats))  # Right

    # Add a wall in the middle with a gap
    layer.add_wall_region(WallRegion((450, 300, 20, 200), wall_stats))
    layer.add_wall_region(WallRegion((450, 550, 20, 200), wall_stats))

    map_obj.add_layer(layer)
    camera.set_bounds(map_obj.width, map_obj.height)

    # Add a door in the gap
    door = Door((460, 500))
    map_obj.add_level_object(door)

    # Create player on the left side of the wall
    player = Player(position=(300, 500), stats=PLAYER_STATS)
    camera.follow(player)

    # Attach sword
    player.add_weapon("sword", Sword(player, SWORD_STATS["basic"]))

    running = True

    print("Controls:")
    print("  WASD / Arrow keys - Move")
    print("  Mouse - Aim")
    print("  Left click - Attack")
    print("  Walk into the door to open it!")

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        input_manager.update()

        # Update map (including doors)
        map_obj.update(dt, player)

        # Get solid regions
        layer_obj = map_obj.get_layer(0)
        solid_regions = layer_obj.get_solid_regions() if layer_obj else []

        # Update player
        player.update(dt, input_manager, [], camera, speed_factor=1.0)

        # Check door interactions
        map_obj.check_level_object_interactions(player)

        # Collision with walls and doors
        pr = player.radius + 4
        px, py = player.pos.x, player.pos.y
        solid_near = [r for r in solid_regions
                      if r.rect.left - pr < px < r.rect.right + pr
                      and r.rect.top - pr < py < r.rect.bottom + pr]

        # Add solid level objects
        solid_objects = map_obj.get_solid_level_objects()
        all_solid = solid_near + solid_objects

        resolve_entity_vs_regions(player, all_solid)

        map_obj.clamp_entity(player)

        camera.update(dt)

        # Draw
        screen.fill(BACKGROUND_COLOR)
        map_obj.draw(screen, camera, player.current_layer)
        player.draw(screen, camera)
        map_obj.draw_walls(screen, camera, player.current_layer)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
