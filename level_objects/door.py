import math
import pygame

from level_objects.level_object_base import LevelObject


class Door(LevelObject):
    """A geometric door that swings open away from the player."""

    # Animation states
    STATE_CLOSED = "closed"
    STATE_OPENING = "opening"
    STATE_OPEN = "open"

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
        self.swing_speed = 300.0  # degrees per second (for touch-to-open)
        self.swing_direction = 1  # 1 for clockwise, -1 for counter-clockwise
        self.just_opened = False  # Set to True when door finishes opening

        # Physics properties
        self.max_angle = 100.0  # Can swing past 90 degrees
        self.bounce_factor = 0.6  # How much velocity is retained on bounce
        self.friction = 0.95  # Velocity multiplier per frame (damping)
        self.impact_threshold = 50.0  # Min velocity for impact effects (camera shake)

        # Determine hinge position based on orientation
        # Hinge is on the side closest to the wall
        self._setup_hinge()

    def _setup_hinge(self):
        """Set up hinge point based on door orientation."""
        if self.orientation == "north":  # Bottom wall, hinge on left
            self.hinge_offset = (-self.door_width / 2, 0)
        elif self.orientation == "south":  # Top wall, hinge on left
            self.hinge_offset = (-self.door_width / 2, 0)
        elif self.orientation == "east":  # Right wall, hinge on top
            self.hinge_offset = (0, -self.door_height / 2)
        elif self.orientation == "west":  # Left wall, hinge on top
            self.hinge_offset = (0, -self.door_height / 2)

    def on_player_touch(self, player):
        """Swing door open into the room it faces."""
        if self.state != self.STATE_CLOSED:
            return

        # Door always swings into the room it faces (away from the wall)
        # This is deterministic based on orientation, not player position
        if self.orientation == "north":  # Bottom wall - swing down (into northern room)
            self.swing_direction = 1
        elif self.orientation == "south":  # Top wall - swing up (into southern room)
            self.swing_direction = -1
        elif self.orientation == "east":  # Right wall - swing right (into eastern room)
            self.swing_direction = 1
        elif self.orientation == "west":  # Left wall - swing left (into western room)
            self.swing_direction = -1

        self.state = self.STATE_OPENING
        self.target_angle = 90.0

    def apply_force(self, angular_impulse):
        """Apply an angular impulse to the door (e.g., from sword hit).

        Parameters
        ----------
        angular_impulse : float
            Angular velocity to add (degrees per second)
        """
        # Determine swing direction if door is closed
        if self.state == self.STATE_CLOSED:
            # Set direction based on sign of impulse, or use default
            if angular_impulse != 0:
                self.swing_direction = 1 if angular_impulse > 0 else -1
            self.state = self.STATE_OPENING

        # Add to angular velocity (physics-based swinging)
        self.angular_velocity += angular_impulse * self.swing_direction

    def get_visibility_rect(self):
        """Get the axis-aligned bounding box of the door in its current rotation.

        This is used for visibility blocking - the rotated door shape blocks vision.
        """
        # Get hinge position in world space
        hinge_world = (
            self.pos.x + self.hinge_offset[0],
            self.pos.y + self.hinge_offset[1]
        )

        # Calculate the four corners of the door rectangle
        if self.orientation in ("north", "south"):
            half_w = self.door_width / 2
            half_h = self.door_height / 2
        else:
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
        """Update door swing animation with physics."""
        self.impact_this_frame = False  # Reset impact flag

        if self.state == self.STATE_OPENING or self.state == self.STATE_OPEN:
            # Physics-based swinging with angular velocity
            if abs(self.angular_velocity) > 0.1:
                # Update angle based on velocity
                self.swing_angle += self.angular_velocity * dt

                # Apply friction/damping
                self.angular_velocity *= self.friction

                # Bounce off max angle
                if self.swing_angle >= self.max_angle:
                    self.swing_angle = self.max_angle
                    self.angular_velocity = -self.angular_velocity * self.bounce_factor

                    # Impact effect if bouncing hard enough
                    if abs(self.angular_velocity) > self.impact_threshold:
                        self.impact_this_frame = True

                # Bounce off closed position
                elif self.swing_angle <= 0:
                    self.swing_angle = 0
                    self.angular_velocity = -self.angular_velocity * self.bounce_factor

                    if abs(self.angular_velocity) > self.impact_threshold:
                        self.impact_this_frame = True

                # Check if door reached open position for first time
                if self.swing_angle >= 90.0 and not self.just_opened:
                    self.just_opened = True
                    self.state = self.STATE_OPEN

            else:
                # No velocity - use simple animation for touch-to-open
                if abs(self.swing_angle - self.target_angle) > 0.1:
                    delta = self.swing_speed * dt
                    if self.swing_angle < self.target_angle:
                        self.swing_angle = min(self.swing_angle + delta, self.target_angle)
                    else:
                        self.swing_angle = max(self.swing_angle - delta, self.target_angle)
                else:
                    # Finished opening
                    self.swing_angle = self.target_angle
                    self.state = self.STATE_OPEN
                    if not self.just_opened:
                        self.just_opened = True

        elif self.state == self.STATE_CLOSED:
            self.swing_angle = 0.0
            self.angular_velocity = 0.0

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

        # Calculate the four corners of the door rectangle before rotation
        if self.orientation in ("north", "south"):
            # Horizontal door
            half_w = self.door_width / 2
            half_h = self.door_height / 2
            corners = [
                (-half_w, -half_h),  # Top-left
                (half_w, -half_h),   # Top-right
                (half_w, half_h),    # Bottom-right
                (-half_w, half_h)    # Bottom-left
            ]
        else:
            # Vertical door
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
