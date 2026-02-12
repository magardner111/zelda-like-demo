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
        Does nothing if already swinging.
        """
        if self.active:
            return

        self.active = True
        self.timer = self.swing_time
        self.hit_this_swing = False

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
                    enemy.take_damage(self.damage, self.owner.pos)
                    self.hit_this_swing = True
                    break

        # End swing
        if self.timer <= 0:
            self.active = False
            self.afterimages.clear()

        # Update afterimages
        for a in self.afterimages:
            a["time"] -= dt

        self.afterimages = [a for a in self.afterimages if a["time"] > 0]

    # =====================================================
    # COLLISION
    # =====================================================

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
