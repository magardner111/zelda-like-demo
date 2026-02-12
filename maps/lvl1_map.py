from maps.map_base import MapBase
from enemies.lvl1enemy import Lvl1Enemy
from settings import WIDTH, HEIGHT


class Lvl1Map(MapBase):
    def __init__(self):
        super().__init__()

        # Place one enemy in center
        self.enemies.append(
            Lvl1Enemy((WIDTH // 2, HEIGHT // 2))
        )
