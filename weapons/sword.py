import pygame
import random
import math


class Sword:
    def __init__(self, owner, data, attack_sounds=None):
        """
        owner: Player instance
        data: dict containing sword stats
        attack_sounds: optional list of pygame.Sound
        """
        self.owner = owner

        # --- Config ---
        self.range = data["range"]
        self.arc_degrees = data["arc_degrees"]
        self.swing_time = data["swing_time"]
        self.afterimage_time = data["afterimage_time"]
        self.damage = data.get("damage", 1)
        self.knockback = data.get("knockback", 0)
        self.sneak_bonus = data.get("sneak_bonus", 0)
        self.stamina_cost = data.get("stamina_cost", 0)

        # --- Runtime ---
        self.timer = 0.0
        self.active = False
        self.hit_this_swing = False

        self.afterimages = []

        self.attack_sounds = attack_sounds or []

    # =====================================================
    # ATTACK CONTROL
    # =====================================================

    def start_attack(self):
        """
        Begin a sword swing.
        Does nothing if already swinging or not enough stamina.
        """
        if self.active:
            return
        if self.owner.stamina < self.stamina_cost:
            return
        self.owner.stamina -= self.stamina_cost

        self.active = True
        self.timer = self.swing_time
        self.hit_this_swing = False
        self.sneaking_at_start = self.owner.sneaking

        # Play random attack sound if provided
        if self.attack_sounds:
            random.choice(self.attack_sounds).play()

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, dt, enemies):
        """
        Update sword animation and check collisions.
        enemies: list of Enemy instances
        """
        if not self.active:
            return

        self.timer -= dt

        progress = 1 - (self.timer / self.swing_time)

        # Compute arc angle
        angle = -self.arc_degrees / 2 + progress * self.arc_degrees
        direction = self.owner.facing.rotate(angle)

        tip = self.owner.pos + direction * self.range

        # Store afterimage
        self.afterimages.append({
            "progress": progress,
            "time": self.afterimage_time
        })

        # Collision (single hit per swing)
        if not self.hit_this_swing:
            for enemy in enemies:
                if self._tip_hits_enemy(tip, enemy):
                    damage = self.damage
                    if self.sneak_bonus and self.sneaking_at_start and enemy.phase != "alerted":
                        damage += self.sneak_bonus
                        self.owner.sneak_attack_timer = self.owner.sneak_attack_duration
                        self._alert_nearby_enemies(enemies)
                    enemy.take_damage(damage, self.owner.pos, self.knockback)
                    self.hit_this_swing = True
                    break

        # End swing
        if self.timer <= 0:
            self.active = False
            if self.sneaking_at_start and not self.hit_this_swing:
                self._alert_nearby_enemies(enemies)
            self.afterimages.clear()

        # Update afterimages
        for a in self.afterimages:
            a["time"] -= dt

        self.afterimages = [a for a in self.afterimages if a["time"] > 0]

    # =====================================================
    # COLLISION
    # =====================================================

    def _alert_nearby_enemies(self, enemies):
        """Alert enemies within their alert radius to face the player."""
        for enemy in enemies:
            if enemy.current_layer != self.owner.current_layer:
                continue
            dist_sq = (enemy.pos - self.owner.pos).length_squared()
            if dist_sq <= enemy.alert_radius ** 2:
                enemy.phase = "alerted"
                enemy.alert_timer = enemy.alert_cooldown
                enemy._last_known_player_pos = pygame.Vector2(self.owner.pos)
                direction = self.owner.pos - enemy.pos
                if direction.length_squared() > 0:
                    enemy.facing = direction.normalize()

    def _tip_hits_enemy(self, tip, enemy):
        """
        Checks if sword tip hits circular enemy.
        Slight radius padding for better feel.
        """
        hit_radius = 6  # small forgiveness radius
        return tip.distance_to(enemy.pos) <= (enemy.size + hit_radius)

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen, camera):
        # Draw afterimages
        for a in self.afterimages:
            ang = -self.arc_degrees / 2 + a["progress"] * self.arc_degrees
            d = self.owner.facing.rotate(ang)

            start = camera.apply(self.owner.pos)
            end = camera.apply(self.owner.pos + d * self.range)

            pygame.draw.line(
                screen,
                (255, 255, 255),
                start,
                end,
                3
            )

        # Draw active blade
        if self.active:
            progress = 1 - (self.timer / self.swing_time)
            ang = -self.arc_degrees / 2 + progress * self.arc_degrees
            d = self.owner.facing.rotate(ang)

            start = camera.apply(self.owner.pos)
            end = camera.apply(self.owner.pos + d * self.range)

            pygame.draw.line(
                screen,
                (255, 255, 255),
                start,
                end,
                5
            )

    # =====================================================
    # MOVEMENT LOCK CHECK
    # =====================================================

    def is_active(self):
        return self.active
