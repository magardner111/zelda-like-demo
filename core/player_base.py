import pygame
from settings import WIDTH, HEIGHT


class Player:
    def __init__(self, position, stats):
        # -----------------------------
        # Position / Movement
        # -----------------------------
        self.pos = pygame.Vector2(position)
        self.vel = pygame.Vector2(0, 0)

        self.radius = stats["radius"]
        self.speed = stats["speed"]
        self.color = stats["color"]

        # IMPORTANT: default facing UP (matches original sword demo)
        self.facing = pygame.Vector2(0, -1)

        # -----------------------------
        # Health
        # -----------------------------
        self.max_health = stats["max_health"]
        self.health = self.max_health

        self.invuln_time = stats["invuln_time"]
        self.invuln_timer = 0.0

        self.knockback_force = stats["knockback_force"]
        self.knockback_timer = 0.0

        # -----------------------------
        # Weapons
        # -----------------------------
        self.weapons = {}
        self.projectiles = []

    # =====================================================
    # WEAPON MANAGEMENT
    # =====================================================

    def add_weapon(self, name, weapon):
        self.weapons[name] = weapon

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, dt, input_manager, enemies):
        self._update_timers(dt)

        sword = self.weapons.get("sword")
        arrow = self.weapons.get("arrow")

        # -----------------------------
        # Movement Lock During Sword
        # -----------------------------
        movement_locked = sword.is_active() if sword else False

        if not movement_locked:
            self._handle_movement(dt, input_manager)

        # -----------------------------
        # Weapon Triggers
        # -----------------------------
        if sword and input_manager.is_pressed("sword"):
            sword.start_attack()

        if arrow and input_manager.is_pressed("arrow"):
            projectile = arrow.start_attack(self.facing)
            if projectile:
                self.projectiles.append(projectile)

        # -----------------------------
        # Weapon Updates
        # -----------------------------
        if sword:
            sword.update(dt, enemies)

        if arrow:
            arrow.update(dt)

        # -----------------------------
        # Projectile Updates
        # -----------------------------
        for p in self.projectiles:
            p.update(dt, enemies)

        self.projectiles = [p for p in self.projectiles if not p.destroyed]

        # -----------------------------
        # Clamp To Screen
        # -----------------------------
        self._clamp_to_screen()

    # =====================================================
    # MOVEMENT
    # =====================================================

    def _handle_movement(self, dt, input_manager):
        move = pygame.Vector2(
            input_manager.is_down("move_right") - input_manager.is_down("move_left"),
            input_manager.is_down("move_down") - input_manager.is_down("move_up"),
        )

        if move.length_squared() > 0:
            move = move.normalize()
            self.pos += move * self.speed * dt
            self.facing = move

    # =====================================================
    # DAMAGE
    # =====================================================

    def take_damage(self, amount, source_position):
        if self.invuln_timer > 0:
            return

        self.health -= amount
        self.invuln_timer = self.invuln_time

        direction = self.pos - source_position
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.vel = direction * self.knockback_force
            self.knockback_timer = 0.2

    # =====================================================
    # TIMERS
    # =====================================================

    def _update_timers(self, dt):
        if self.invuln_timer > 0:
            self.invuln_timer -= dt

        if self.knockback_timer > 0:
            self.knockback_timer -= dt
            self.pos += self.vel * dt
            self.vel *= 0.85

    # =====================================================
    # SCREEN BOUNDS
    # =====================================================

    def _clamp_to_screen(self):
        self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(HEIGHT - self.radius, self.pos.y))

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen, camera):
        # Flash white while invulnerable
        color = (255, 255, 255) if self.invuln_timer > 0 else self.color

        pygame.draw.circle(
            screen,
            color,
            camera.apply(self.pos),
            self.radius
        )

        # Draw Sword
        sword = self.weapons.get("sword")
        if sword:
            sword.draw(screen, camera)

        # Draw Projectiles
        for p in self.projectiles:
            p.draw(screen, camera)
