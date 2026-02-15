import os

from maps.map_base import MapBase
from enemies.lvl1enemy import Lvl1Enemy


class Lvl1Map(MapBase):
    def __init__(self):
        json_path = os.path.join(os.path.dirname(__file__), "lvl1.json")
        loaded = MapBase.from_json(json_path)
        super().__init__(width=loaded.width, height=loaded.height)
        self.floor_layers = loaded.floor_layers
        self.stairways = loaded.stairways

        self._place_enemies()

    def _place_enemies(self):
        # Ground floor enemy
        enemy0 = Lvl1Enemy((self.width // 2, self.height // 2))
        enemy0.current_layer = 0
        self.enemies.append(enemy0)

        # Platform enemy
        enemy1 = Lvl1Enemy((500, 750))
        enemy1.current_layer = 1
        self.enemies.append(enemy1)
