import math
import pygame

from level_objects.level_object_base import LevelObject


class Door(LevelObject):
    """A geometric door that swings open away from the player."""

    # Animation states
    STATE_CLOSED = "closed"
    STATE_OPENING = "opening"
    STATE_OPEN = "open"

    def __init__(self, position, orientation="north"):
        """Create a swinging door.

        Parameters
        ----------
        position : tuple
            (x, y) position in world coordinates (center of doorway)
        orientation : str
            Which wall the door is on: "north", "south", "east", "west"
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

        # Visual properties
        self.door_color = (101, 67, 33)  # Brown wood color
        self.door_edge_color = (70, 46, 23)  # Darker edge
        self.hinge_color = (40, 40, 40)  # Dark gray hinge

        # Animation state
        self.state = self.STATE_CLOSED
        self.swing_angle = 0.0  # Current rotation angle (0 = closed, 90 = open)
        self.target_angle = 0.0
        self.swing_speed = 300.0  # degrees per second
        self.swing_direction = 1  # 1 for clockwise, -1 for counter-clockwise

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
        """Swing door open away from the player."""
        if self.state != self.STATE_CLOSED:
            return

        # Determine which side the player is approaching from
        dx = player.pos.x - self.pos.x
        dy = player.pos.y - self.pos.y

        # Set swing direction based on player position relative to door
        if self.orientation == "north":  # Bottom wall
            # Player coming from bottom (inside room) -> swing down
            # Player coming from top (outside room) -> swing up
            self.swing_direction = 1 if dy < 0 else -1
        elif self.orientation == "south":  # Top wall
            self.swing_direction = 1 if dy > 0 else -1
        elif self.orientation == "east":  # Right wall
            self.swing_direction = 1 if dx < 0 else -1
        elif self.orientation == "west":  # Left wall
            self.swing_direction = 1 if dx > 0 else -1

        self.state = self.STATE_OPENING
        self.target_angle = 90.0

    def update(self, dt):
        """Update door swing animation."""
        if self.state == self.STATE_OPENING:
            # Animate swing
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
                self.solid = False  # Door stays visible but non-solid

        elif self.state == self.STATE_CLOSED:
            self.swing_angle = 0.0
            self.solid = True

        elif self.state == self.STATE_OPEN:
            self.solid = False

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
