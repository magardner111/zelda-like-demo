import os
import pygame

from level_objects.level_object_base import LevelObject


class Door(LevelObject):
    """An animated door that blocks the player until opened on touch."""

    # Animation states
    STATE_CLOSED = "closed"
    STATE_OPENING = "opening"
    STATE_OPEN = "open"

    def __init__(self, position, orientation="north", image_path=None):
        """Create a door.

        Parameters
        ----------
        position : tuple
            (x, y) position in world coordinates
        orientation : str
            Direction the door faces: "north", "south", "east", "west"
        image_path : str, optional
            Path to custom door sprite sheet
        """
        super().__init__(position, size=(64, 64))

        self.orientation = orientation

        # Load door sprite sheet (3 frames: closed, opening, open)
        if image_path is None:
            image_path = os.path.join(
                os.path.dirname(__file__),
                "..", "assets", "level_objects", "dungeon", "door.png"
            )

        sprite_sheet = pygame.image.load(image_path).convert_alpha()
        frame_width = 64

        # Extract frames from the sprite sheet
        self.frames = []
        for i in range(3):
            frame = sprite_sheet.subsurface(
                pygame.Rect(i * frame_width, 0, frame_width, frame_width)
            )

            # Rotate frames for vertical doors (east/west walls)
            if orientation in ("east", "west"):
                frame = pygame.transform.rotate(frame, 90)

            self.frames.append(frame)

        # Animation state
        self.state = self.STATE_CLOSED
        self.current_frame = 0
        self.anim_timer = 0.0
        self.frame_duration = 0.15  # seconds per frame during opening animation

    def on_player_touch(self, player):
        """Open the door when the player touches it."""
        if self.state == self.STATE_CLOSED:
            self.state = self.STATE_OPENING
            self.anim_timer = 0.0
            self.current_frame = 0

    def update(self, dt):
        """Update door animation."""
        if self.state == self.STATE_OPENING:
            self.anim_timer += dt

            # Advance through frames
            if self.anim_timer >= self.frame_duration:
                self.anim_timer -= self.frame_duration
                self.current_frame += 1

                # Finish opening animation
                if self.current_frame >= len(self.frames):
                    self.current_frame = len(self.frames) - 1
                    self.state = self.STATE_OPEN
                    self.solid = False  # Allow player to pass through

        elif self.state == self.STATE_CLOSED:
            self.current_frame = 0
            self.solid = True

        elif self.state == self.STATE_OPEN:
            self.current_frame = len(self.frames) - 1
            self.solid = False

    def draw(self, screen, camera):
        """Draw the current door frame."""
        if not self.active:
            return

        screen_pos = camera.apply(self.pos)
        frame = self.frames[self.current_frame]

        # Center the frame on the door position
        draw_rect = frame.get_rect(center=(screen_pos.x, screen_pos.y))
        screen.blit(frame, draw_rect)
