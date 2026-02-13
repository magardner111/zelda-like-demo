from maps.map_base import MapBase
from core.floor_layer import FloorLayer
from core.stairway import Stairway
from core.region_base import WallRegion, FloorRegion, LiquidRegion, ObjectRegion
from data.region_stats import REGION_STATS
from enemies.lvl1enemy import Lvl1Enemy


class Lvl1Map(MapBase):
    def __init__(self):
        super().__init__(width=1024, height=1024)

        self._build_ground_floor()
        self._build_platform()
        self._build_stairways()
        self._place_enemies()

    def _build_ground_floor(self):
        layer = FloorLayer(elevation=0, bg_color=(72, 60, 50))

        wall = REGION_STATS["wall"]
        t = 32  # wall thickness

        # Border walls
        layer.add_wall_region(WallRegion((0, 0, self.width, t), wall))              # top
        layer.add_wall_region(WallRegion((0, self.height - t, self.width, t), wall)) # bottom
        layer.add_wall_region(WallRegion((0, 0, t, self.height), wall))              # left
        layer.add_wall_region(WallRegion((self.width - t, 0, t, self.height), wall)) # right

        # Water pool
        layer.add_floor_region(
            LiquidRegion((200, 200, 180, 140), "water", REGION_STATS["water"])
        )

        # Grass patch
        layer.add_floor_region(
            FloorRegion((500, 100, 200, 200), "grass", REGION_STATS["grass"])
        )

        # Stone path
        layer.add_floor_region(
            FloorRegion((450, 400, 120, 300), "stone", REGION_STATS["stone"])
        )

        # Chest
        layer.add_floor_region(
            ObjectRegion((700, 150, 40, 40), "chest", REGION_STATS["chest"])
        )

        # Interior wall
        layer.add_wall_region(WallRegion((600, 500, 200, 32), wall))

        self.add_layer(layer)

    def _build_platform(self):
        layer = FloorLayer(elevation=1, bg_color=(90, 85, 78))

        wall = REGION_STATS["wall"]

        # Stone floor area
        layer.add_floor_region(
            FloorRegion((350, 600, 300, 300), "stone", REGION_STATS["stone"])
        )

        # Enclosing walls (with gap for stairway)
        layer.add_wall_region(WallRegion((350, 600, 300, 24), wall))   # top
        layer.add_wall_region(WallRegion((350, 876, 300, 24), wall))   # bottom
        #layer.add_wall_region(WallRegion((350, 600, 24, 300), wall))   # left
        layer.add_wall_region(WallRegion((626, 600, 24, 120), wall))   # right top
        layer.add_wall_region(WallRegion((626, 780, 24, 120), wall))   # right bottom (gap 720-780)

        self.add_layer(layer)

    def _build_stairways(self):
        # Stairway on the right side of the platform, in the gap
        self.add_stairway(
            Stairway((650, 720, 40, 60), from_layer=0, to_layer=1)
        )

    def _place_enemies(self):
        # Ground floor enemy
        enemy0 = Lvl1Enemy((self.width // 2, self.height // 2))
        enemy0.current_layer = 0
        self.enemies.append(enemy0)

        # Platform enemy
        enemy1 = Lvl1Enemy((500, 750))
        enemy1.current_layer = 1
        self.enemies.append(enemy1)
