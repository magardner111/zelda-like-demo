import pygame


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

        self.facing_line_color = stats["facing_line_color"]
        self.facing_line_length = stats["facing_line_length"]
        self.facing_line_offset = stats["facing_line_offset"]

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
        # Stamina
        # -----------------------------
        self.max_stamina = stats["max_stamina"]
        self.stamina = self.max_stamina
        self.stamina_regen = stats["stamina_regen"]

        # -----------------------------
        # Dodge
        # -----------------------------
        self.dodge_stamina_cost = stats["dodge_stamina_cost"]
        self.dodge_distance = stats["dodge_distance"]
        self.dodge_speed = stats["dodge_speed"]
        self.dodge_remaining = 0.0
        self.dodge_direction = pygame.Vector2(0, 0)

        # -----------------------------
        # Sneak
        # -----------------------------
        self.sneak_speed_factor = stats["sneak_speed_factor"]
        self.sneaking = False

        # -----------------------------
        # Layer
        # -----------------------------
        self.current_layer = 0

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

    def update(self, dt, input_manager, enemies, camera, speed_factor=1.0):
        self._update_timers(dt)

        sword = self.weapons.get("sword")
        arrow = self.weapons.get("arrow")

        # -----------------------------
        # Lock Movement & Facing During Attack/Dodge
        # -----------------------------
        attack_active = sword.is_active() if sword else False
        dodging = self.dodge_remaining > 0

        self.sneaking = (not attack_active and not dodging
                         and input_manager.is_down("sneak"))

        if not attack_active and not dodging:
            self._update_facing(input_manager, camera)
            self._handle_movement(dt, input_manager, speed_factor)

        # -----------------------------
        # Dodge Trigger
        # -----------------------------
        if input_manager.is_pressed("dodge") and not dodging and not attack_active:
            if self.stamina >= self.dodge_stamina_cost:
                self.stamina -= self.dodge_stamina_cost
                self.dodge_remaining = self.dodge_distance
                self.dodge_direction = -self.facing

        # -----------------------------
        # Weapon Triggers
        # -----------------------------
        if sword and input_manager.is_pressed("sword") and not dodging:
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

    # =====================================================
    # MOVEMENT
    # =====================================================

    def _handle_movement(self, dt, input_manager, speed_factor=1.0):
        move = pygame.Vector2(
            input_manager.is_down("move_right") - input_manager.is_down("move_left"),
            input_manager.is_down("move_down") - input_manager.is_down("move_up"),
        )

        if move.length_squared() > 0:
            move = move.normalize()
            speed = self.invuln_speed if self.invuln_timer > 0 else self.speed
            if self.sneaking:
                speed *= self.sneak_speed_factor
            speed *= speed_factor
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

        # Dodge movement
        if self.dodge_remaining > 0:
            step = self.dodge_speed * dt
            if step > self.dodge_remaining:
                step = self.dodge_remaining
            self.pos += self.dodge_direction * step
            self.dodge_remaining -= step

        # Stamina regen
        if self.stamina < self.max_stamina:
            self.stamina = min(self.max_stamina, self.stamina + self.stamina_regen * dt)

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen, camera):
        color = self.color
        if self.sneaking:
            color = (color[0] // 2, color[1] // 2, color[2] // 2)

        # Blink transparency while invulnerable
        if self.invuln_timer > 0 and int(self.invuln_timer * self.invuln_freq * 2) % 2 == 0:
            surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, 128), (self.radius, self.radius), self.radius)
            screen.blit(surf, camera.apply(self.pos) - pygame.Vector2(self.radius, self.radius))
        else:
            pygame.draw.circle(screen, color, camera.apply(self.pos), self.radius)

        # Facing indicator line
        screen_pos = camera.apply(self.pos)
        line_start = screen_pos + self.facing * self.facing_line_offset
        line_end = screen_pos + self.facing * (self.facing_line_offset + self.facing_line_length)
        pygame.draw.line(screen, self.facing_line_color, line_start, line_end, 2)

        # Draw Sword
        sword = self.weapons.get("sword")
        if sword:
            sword.draw(screen, camera)

        # Draw Projectiles
        for p in self.projectiles:
            p.draw(screen, camera)
