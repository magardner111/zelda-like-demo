from settings import WIDTH, HEIGHT
from core.hud_base import HudLayer, HudContainer, HudBar

# Pixels of bar width per unit of max stat
HP_BAR_SCALE = 10
STAMINA_BAR_SCALE = 1


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
        bar_height = 20
        bar_gap = 6
        hp_bar_width = player.max_health * HP_BAR_SCALE
        top_bar.add(HudBar(
            position=(padding, padding),
            size=(hp_bar_width, bar_height),
            value_source=lambda: player.health,
            max_source=lambda: player.max_health,
            bar_color=(220, 50, 50),
            bg_color=(60, 60, 60),
            border_color=(180, 180, 180),
            border_width=1,
        ))

        # Stamina bar — below health bar, width scales with max stamina
        stamina_bar_width = player.max_stamina * STAMINA_BAR_SCALE
        top_bar.add(HudBar(
            position=(padding, padding + bar_height + bar_gap),
            size=(stamina_bar_width, bar_height),
            value_source=lambda: player.stamina,
            max_source=lambda: player.max_stamina,
            bar_color=(50, 180, 50),
            bg_color=(60, 60, 60),
            border_color=(180, 180, 180),
            border_width=1,
        ))
