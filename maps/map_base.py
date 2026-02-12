class MapBase:
    def __init__(self):
        self.enemies = []

    def update(self, dt, player):
        for enemy in self.enemies:
            enemy.update(dt, player)

    def draw(self, screen, camera):
        for enemy in self.enemies:
            enemy.draw(screen, camera)
