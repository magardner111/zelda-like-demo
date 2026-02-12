import pygame


def check_player_enemy_collisions(player, enemies):
    """Check if player overlaps any enemy (circle vs square). Apply damage on contact."""
    for enemy in enemies:
        if enemy.health <= 0:
            continue

        # Closest point on enemy rect to player center
        half = enemy.size
        closest_x = max(enemy.pos.x - half, min(player.pos.x, enemy.pos.x + half))
        closest_y = max(enemy.pos.y - half, min(player.pos.y, enemy.pos.y + half))

        dist_sq = (player.pos.x - closest_x) ** 2 + (player.pos.y - closest_y) ** 2

        if dist_sq < player.radius ** 2:
            player.take_damage(enemy.hit_damage, enemy.pos)
