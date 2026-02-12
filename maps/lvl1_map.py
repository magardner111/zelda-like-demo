from maps.map_base import MapBase
from enemies.lvl1enemy import Lvl1Enemy


class Lvl1Map(MapBase):
    def __init__(self):
        super().__init__(
            width=1024,
            height=1024,
            bg_color=(72, 60, 50),
        )

        # Place one enemy in center of map
        self.enemies.append(
            Lvl1Enemy((self.width // 2, self.height // 2))
        )
