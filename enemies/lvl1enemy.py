from core.enemy_base import Enemy
from data.enemy_stats import ENEMY_STATS
from patterns.enemy_patterns import UpDownPattern




class Lvl1Enemy(Enemy):
    def __init__(self, position):
        super().__init__(
            position=position,
            stats=ENEMY_STATS["lvl1enemy"]
        )

        # Back and forth pattern
        self.pattern = UpDownPattern(distance=200, pause_time=2.5, speed=60)

    # You can override update later if needed
    # For now, it just uses base behavior
