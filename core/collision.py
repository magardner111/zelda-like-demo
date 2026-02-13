import pygame

from core.region_base import LiquidRegion


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


def resolve_entity_vs_regions(entity, regions):
    """Push entity out of solid regions along shortest overlap axis."""
    r = getattr(entity, "radius", 0)

    for region in regions:
        if not region.overlaps_circle(entity.pos, r):
            continue

        # Find overlap on each axis
        half_w = region.rect.width / 2
        half_h = region.rect.height / 2
        cx = region.rect.centerx
        cy = region.rect.centery

        dx = entity.pos.x - cx
        dy = entity.pos.y - cy

        overlap_x = half_w + r - abs(dx)
        overlap_y = half_h + r - abs(dy)

        if overlap_x <= 0 or overlap_y <= 0:
            continue

        # Push along shortest axis
        if overlap_x < overlap_y:
            if dx > 0:
                entity.pos.x += overlap_x
            else:
                entity.pos.x -= overlap_x
        else:
            if dy > 0:
                entity.pos.y += overlap_y
            else:
                entity.pos.y -= overlap_y


def apply_region_effects(entity, regions, dt):
    """Apply effects from overlapping non-solid regions. Returns min speed_factor."""
    r = getattr(entity, "radius", 0)
    min_speed_factor = 1.0

    for region in regions:
        if not region.overlaps_circle(entity.pos, r):
            continue

        if isinstance(region, LiquidRegion):
            region.apply_effects(entity, dt)
            if region.speed_factor < min_speed_factor:
                min_speed_factor = region.speed_factor

    return min_speed_factor
