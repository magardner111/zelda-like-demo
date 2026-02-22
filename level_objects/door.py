import math
import pygame

from level_objects.level_object_base import LevelObject


class Door(LevelObject):
    """A geometric door that swings open away from the player."""

    # Camera shake applied on sword hit and dash slam (duration, intensity)
    SLAM_SHAKE = (0.25, 20)

    # Animation states
    STATE_CLOSED = "closed"
    STATE_OPENING = "opening"
    STATE_OPEN = "open"
    STATE_CLOSING = "closing"

    def __init__(self, position, orientation="north", connected_rooms=None):
        """Create a swinging door.

        Parameters
        ----------
        position : tuple
            (x, y) position in world coordinates (center of doorway)
        orientation : str
            Which wall the door is on: "north", "south", "east", "west"
        connected_rooms : tuple, optional
            (room_id_1, room_id_2) - the two rooms this door connects
        """
        # Door dimensions based on orientation
        if orientation in ("north", "south"):
            width, height = 64, 12  # Horizontal door
        else:
            width, height = 12, 64  # Vertical door

        super().__init__(position, size=(width, height))

        self.orientation = orientation
        self.door_width = width
        self.door_height = height
        self.connected_rooms = connected_rooms or ()

        # Visual properties
        self.door_color = (101, 67, 33)  # Brown wood color
        self.door_edge_color = (70, 46, 23)  # Darker edge
        self.hinge_color = (40, 40, 40)  # Dark gray hinge

        # Animation state
        self.state = self.STATE_CLOSED
        self.swing_angle = 0.0  # Current rotation angle (0 = closed, 90 = open)
        self.angular_velocity = 0.0  # degrees per second (physics-based)
        self.target_angle = 0.0
        self.swing_speed = 200.0  # degrees per second (for touch/close)
        self.swing_direction = 1  # 1 for clockwise, -1 for counter-clockwise
        self.just_opened = False  # Set to True when door finishes opening
        self.solid = False  # Player walks through — door opens on contact

        # Physics properties
        self.max_angle = 110.0  # Allow door to overshoot past perpendicular
        self.rest_angle = 100.0  # Settle slightly past perpendicular
        self.friction = 0.92  # Velocity multiplier per frame (damping)
        self.impact_threshold = 80.0  # Min velocity for impact effects (camera shake)
        self.door_damage = 3
        self.door_knockback = 350
        self._enemies_hit_this_swing = set()  # avoid repeat hits per swing
        self._sword_hit = False  # only sword hits cause impact/damage
        self._sword_impact = False  # camera shake on sword connect

        # Determine hinge position based on orientation
        # Hinge is on the side closest to the wall
        self._setup_hinge()

    def _setup_hinge(self):
        """Set up hinge point at the edge of the door (on a wall)."""
        if self.orientation in ("north", "south"):
            # Horizontal door - hinge on left side
            self.hinge_offset = (-self.door_width / 2, 0)
        else:
            # Vertical door - hinge on top side
            self.hinge_offset = (0, -self.door_height / 2)

    def _swing_direction_from(self, source_pos):
        """Return +1 or -1 so the door swings away from *source_pos*.

        Horizontal doors (north/south wall): hinge at left edge, door extends
        right.  Positive rotation swings the far end downward (increasing y).
          - source above (dy < 0) → swing down (+1)
          - source below (dy > 0) → swing up   (-1)

        Vertical doors (east/west wall): hinge at top edge, door extends down.
        Positive rotation swings the far end to the left (decreasing x).
          - source to the right (dx > 0) → swing left  (+1)
          - source to the left  (dx < 0) → swing right (-1)
        """
        if self.orientation in ("north", "south"):
            dy = source_pos.y - self.pos.y if hasattr(source_pos, 'y') else source_pos[1] - self.pos.y
            return 1 if dy < 0 else -1
        else:
            dx = source_pos.x - self.pos.x if hasattr(source_pos, 'x') else source_pos[0] - self.pos.x
            return -1 if dx < 0 else 1

    def on_player_touch(self, player):
        """Door swings away from player like pushing a door open."""
        if self.state != self.STATE_CLOSED:
            return

        self.swing_direction = self._swing_direction_from(player.pos)
        self._enemies_hit_this_swing = set()

        # Dashing through a door slams it open like a sword hit
        if getattr(player, 'dodge_remaining', 0) > 0:
            self.state = self.STATE_OPENING
            self.angular_velocity = player.dodge_speed * 1.5
            self._sword_hit = True
            player._pending_shake = self.SLAM_SHAKE
        else:
            self.state = self.STATE_OPENING

    def on_enemy_touch(self, enemy):
        """Door swings away from enemy like pushing a door open."""
        if self.state != self.STATE_CLOSED:
            return

        self.swing_direction = self._swing_direction_from(enemy.pos)
        self.state = self.STATE_OPENING
        self._enemies_hit_this_swing = set()

    def apply_force(self, angular_impulse, source_pos):
        """Apply an angular impulse to the door (e.g., from sword hit).

        Parameters
        ----------
        angular_impulse : float
            Angular velocity to add (degrees per second)
        source_pos : Vector2
            Position of the force source (player) to determine swing direction
        """
        self._enemies_hit_this_swing = set()
        self._sword_hit = True
        self._sword_impact = True

        if self.state == self.STATE_CLOSED:
            # Open: swing away from source
            self.swing_direction = self._swing_direction_from(source_pos)
            self.state = self.STATE_OPENING
            self.angular_velocity += angular_impulse
        elif self.state in (self.STATE_OPEN, self.STATE_OPENING):
            # Slam closed
            self.state = self.STATE_CLOSING
            self.angular_velocity = -angular_impulse
        elif self.state == self.STATE_CLOSING:
            # Already closing — add more force
            self.angular_velocity -= angular_impulse

    def get_visibility_rect(self):
        """Get the axis-aligned bounding box of the door in its current rotation.

        This is used for visibility blocking - the rotated door shape blocks vision.
        """
        # Get hinge position in world space
        hinge_world = (
            self.pos.x + self.hinge_offset[0],
            self.pos.y + self.hinge_offset[1]
        )

        # Calculate the four corners of the door rectangle (same as draw method)
        # Corners are defined relative to door center
        half_w = self.door_width / 2
        half_h = self.door_height / 2

        corners = [
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h)
        ]

        # Apply rotation around hinge point
        angle_rad = math.radians(self.swing_angle * self.swing_direction)
        rotated_corners = []

        for cx, cy in corners:
            # Translate to hinge origin
            px = cx - self.hinge_offset[0]
            py = cy - self.hinge_offset[1]

            # Rotate
            rx = px * math.cos(angle_rad) - py * math.sin(angle_rad)
            ry = px * math.sin(angle_rad) + py * math.cos(angle_rad)

            # Translate back to world space
            world_x = hinge_world[0] + rx
            world_y = hinge_world[1] + ry
            rotated_corners.append((world_x, world_y))

        # Find axis-aligned bounding box
        min_x = min(c[0] for c in rotated_corners)
        max_x = max(c[0] for c in rotated_corners)
        min_y = min(c[1] for c in rotated_corners)
        max_y = max(c[1] for c in rotated_corners)

        return pygame.Rect(int(min_x), int(min_y),
                          int(max_x - min_x), int(max_y - min_y))

    def get_collision_rect(self):
        """Get the rect used for player collision (same as visibility rect)."""
        return self.get_visibility_rect()

    def update(self, dt):
        """Update door swing animation."""
        self.impact_this_frame = False

        if self.state == self.STATE_CLOSED:
            self.swing_angle = 0.0
            self.angular_velocity = 0.0
            return

        # --- door is moving ---

        if abs(self.angular_velocity) > 0.1:
            # Physics-driven (sword hit)
            self.swing_angle += self.angular_velocity * dt
            self.angular_velocity *= self.friction

            # Clamp at max angle
            if self.swing_angle >= self.max_angle:
                self.swing_angle = self.max_angle
                if self._sword_hit and abs(self.angular_velocity) > self.impact_threshold:
                    self.impact_this_frame = True
                self.angular_velocity = 0.0

            # Reached closed position
            if self.swing_angle <= 0:
                self.swing_angle = 0.0
                self.angular_velocity = 0.0
                self.state = self.STATE_CLOSED
                self.just_opened = False
                self._enemies_hit_this_swing = set()
                self._sword_hit = False
                return
        else:
            # Smooth animation toward target
            self.angular_velocity = 0.0
            target = 0.0 if self.state == self.STATE_CLOSING else self.rest_angle
            delta = self.swing_speed * dt
            if self.swing_angle < target:
                self.swing_angle = min(self.swing_angle + delta, target)
            elif self.swing_angle > target:
                self.swing_angle = max(self.swing_angle - delta, target)

            # Finished closing
            if self.state == self.STATE_CLOSING and self.swing_angle <= 0.1:
                self.swing_angle = 0.0
                self.state = self.STATE_CLOSED
                self.just_opened = False
                self._enemies_hit_this_swing = set()
                self._sword_hit = False
                return

        # Mark open once we reach the rest angle
        if self.state == self.STATE_OPENING and self.swing_angle >= self.rest_angle:
            if not self.just_opened:
                self.just_opened = True
            self.state = self.STATE_OPEN
            self._enemies_hit_this_swing = set()
            self._sword_hit = False

    def check_enemy_collisions(self, enemies):
        """Damage enemies hit by a swinging door (sword hits only)."""
        if not self._sword_hit:
            return
        if self.state not in (self.STATE_OPENING, self.STATE_CLOSING):
            return

        door_rect = self.get_collision_rect()
        hinge_world = pygame.Vector2(
            self.pos.x + self.hinge_offset[0],
            self.pos.y + self.hinge_offset[1],
        )

        for enemy in enemies:
            if id(enemy) in self._enemies_hit_this_swing:
                continue
            if enemy.health <= 0:
                continue
            # Circle-vs-rect overlap
            closest_x = max(door_rect.left, min(enemy.pos.x, door_rect.right))
            closest_y = max(door_rect.top, min(enemy.pos.y, door_rect.bottom))
            dist_sq = (enemy.pos.x - closest_x) ** 2 + (enemy.pos.y - closest_y) ** 2
            if dist_sq < enemy.size ** 2:
                enemy.take_damage(self.door_damage, hinge_world, self.door_knockback)
                self._enemies_hit_this_swing.add(id(enemy))

    def draw(self, screen, camera):
        """Draw the swinging door."""
        if not self.active:
            return

        screen_pos = camera.apply(self.pos)

        # Get hinge position in world space
        hinge_world = (
            self.pos.x + self.hinge_offset[0],
            self.pos.y + self.hinge_offset[1]
        )
        hinge_screen = camera.apply(pygame.Vector2(hinge_world))

        # Four corners of the door rectangle relative to door center
        half_w = self.door_width / 2
        half_h = self.door_height / 2
        corners = [
            (-half_w, -half_h),
            ( half_w, -half_h),
            ( half_w,  half_h),
            (-half_w,  half_h),
        ]

        # Apply rotation around hinge point
        angle_rad = math.radians(self.swing_angle * self.swing_direction)
        rotated_corners = []

        for cx, cy in corners:
            # Translate to hinge origin
            px = cx - self.hinge_offset[0]
            py = cy - self.hinge_offset[1]

            # Rotate
            rx = px * math.cos(angle_rad) - py * math.sin(angle_rad)
            ry = px * math.sin(angle_rad) + py * math.cos(angle_rad)

            # Translate back and convert to screen space
            world_x = hinge_world[0] + rx
            world_y = hinge_world[1] + ry
            screen_point = camera.apply(pygame.Vector2(world_x, world_y))
            rotated_corners.append((screen_point.x, screen_point.y))

        # Draw door rectangle
        pygame.draw.polygon(screen, self.door_color, rotated_corners)
        pygame.draw.polygon(screen, self.door_edge_color, rotated_corners, 2)

        # Draw hinge as a small circle
        pygame.draw.circle(screen, self.hinge_color,
                          (int(hinge_screen.x), int(hinge_screen.y)), 4)
