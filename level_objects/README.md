# Level Objects System

The `level_objects` module provides a framework for interactable non-actor objects in the game world, such as doors, chests, switches, and pressure plates.

## Architecture

### Base Class: `LevelObject`

All level objects inherit from `level_objects.level_object_base.LevelObject`, which provides:

- **Position and collision**: Objects have a position, size, and rect for collision detection
- **Solid property**: When `solid=True`, the object blocks player movement
- **Active property**: When `active=False`, the object is ignored by the game loop
- **Collision detection**: `overlaps_circle(pos, radius)` method for player interaction
- **Callbacks**: `on_player_touch(player)` called when the player touches the object
- **Update/Draw**: Override `update(dt)` and `draw(screen, camera)` for custom behavior

### Door Implementation

The `Door` class (`level_objects.door.Door`) is the first implementation:

**Features:**
- Three-frame animation: closed → opening → open
- Blocks the player when closed (`solid=True`)
- Opens when the player touches it
- Allows passage when fully open (`solid=False`)
- Uses a sprite sheet with 3 frames (64x64 each)

**States:**
- `STATE_CLOSED`: Door is closed and solid
- `STATE_OPENING`: Animation playing (3 frames at 0.15s each)
- `STATE_OPEN`: Door is open and passable

## Integration with MapBase

The `MapBase` class has been extended to support level objects:

### New Methods

- `add_level_object(obj)`: Add a level object to the map
- `get_solid_level_objects()`: Get all objects that currently block movement
- `check_level_object_interactions(player)`: Check for player-object collisions

### Game Loop Integration

In `main.py`, the following happens each frame:

1. **Update**: `map_obj.update(dt, player)` updates all level objects
2. **Interactions**: `map_obj.check_level_object_interactions(player)` triggers `on_player_touch` callbacks
3. **Collision**: Solid level objects are added to the collision resolution list
4. **Draw**: Level objects are drawn during `map_obj.draw()`

## Usage Examples

### Adding a Door to a Map

```python
from level_objects.door import Door

# Create a door at position (400, 300)
door = Door((400, 300))

# Add it to the map
map_obj.add_level_object(door)
```

### Adding Doors to Generated Maps

Use the `add_door_to_doorway` helper function:

```python
from maps import generate_layout, generate_map, add_door_to_doorway

layout = generate_layout()
map_obj, player_start = generate_map(layout)

# Add a door to the north doorway of the starting room
add_door_to_doorway(map_obj, room_x=0, room_y=0, direction="north")
```

### Creating Custom Level Objects

Subclass `LevelObject` and override the key methods:

```python
from level_objects.level_object_base import LevelObject
import pygame

class Chest(LevelObject):
    def __init__(self, position):
        super().__init__(position, size=(64, 64))
        self.opened = False
        self.solid = True  # Blocks movement

    def on_player_touch(self, player):
        if not self.opened:
            self.opened = True
            self.solid = False  # Can walk through after opening
            print("Chest opened! +100 gold")

    def update(self, dt):
        # Custom update logic
        pass

    def draw(self, screen, camera):
        screen_pos = camera.apply(self.pos)
        color = (255, 215, 0) if self.opened else (139, 69, 19)
        pygame.draw.rect(screen, color,
                        pygame.Rect(screen_pos.x - 32, screen_pos.y - 32, 64, 64))
```

## Asset Requirements

### Door Sprite Sheet

The default door sprite is located at:
```
assets/level_objects/dungeon/door.png
```

Format: 192x64 PNG (3 frames of 64x64):
- Frame 0 (0-63px): Closed
- Frame 1 (64-127px): Opening
- Frame 2 (128-191px): Open

### Custom Door Sprites

Pass a custom image path to the Door constructor:

```python
door = Door((400, 300), image_path="assets/level_objects/my_door.png")
```

## Testing

Run the test script to see a door in action:

```bash
python test_door.py
```

This creates a simple room with a wall and a door. Walk into the door to trigger the opening animation.

## Future Extensions

Potential level objects to implement:

- **Chest**: Opens when touched, grants items
- **Lever/Switch**: Toggles state, can control other objects
- **Pressure Plate**: Triggers when player stands on it
- **Locked Door**: Requires a key to open
- **Trap Door**: Opens when triggered, player falls through
- **Signpost**: Displays text when interacted with
