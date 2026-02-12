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

        self.invuln_freq = stats["invuln_freq"]
        self.invuln_speed = stats["invuln_speed"]

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

    def update(self, dt, input_manager, enemies, camera):
        self._update_timers(dt)
        self._update_facing(input_manager, camera)

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
            speed = self.invuln_speed if self.invuln_timer > 0 else self.speed
            self.pos += move * speed * dt

    # =====================================================
    # FACING (mouse-based)
    # =====================================================

    def _update_facing(self, input_manager, camera):
        mouse_screen = input_manager.get_mouse_pos()
        mouse_world = mouse_screen - camera.offset
        direction = mouse_world - self.pos
        if direction.length() > input_manager.mouse_config["dead_zone"]:
            self.facing = direction.normalize()

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
        # Blink transparency while invulnerable
        if self.invuln_timer > 0 and int(self.invuln_timer * self.invuln_freq * 2) % 2 == 0:
            surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, 128), (self.radius, self.radius), self.radius)
            screen.blit(surf, camera.apply(self.pos) - pygame.Vector2(self.radius, self.radius))
        else:
            pygame.draw.circle(screen, self.color, camera.apply(self.pos), self.radius)

        # Draw Sword
        sword = self.weapons.get("sword")
        if sword:
            sword.draw(screen, camera)

        # Draw Projectiles
        for p in self.projectiles:
            p.draw(screen, camera)
