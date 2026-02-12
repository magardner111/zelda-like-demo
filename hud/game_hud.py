from settings import WIDTH, HEIGHT
from core.hud_base import HudLayer, HudContainer, HudBar

# Pixels of bar width per point of max health
HP_BAR_SCALE = 10


class GameHud(HudLayer):
    """Concrete HUD layout for the game.

    Binds UI elements to player/game data via callables passed at construction.
    """

    def __init__(self, player):
        super().__init__()

        container_height = HEIGHT // 8
        padding = 10

        # Top-bar container spanning full width, 1/8th of screen height
        top_bar = self.add(HudContainer(
            position=(0, 0),
            size=(WIDTH, container_height),
            bg_color=(0, 0, 0, 120),
        ))

        # Health bar — width scales with max health
        bar_width = player.max_health * HP_BAR_SCALE
        bar_height = 20
        top_bar.add(HudBar(
            position=(padding, padding),
            size=(bar_width, bar_height),
            value_source=lambda: player.health,
            max_source=lambda: player.max_health,
            bar_color=(220, 50, 50),
            bg_color=(60, 60, 60),
            border_color=(180, 180, 180),
            border_width=1,
        ))
