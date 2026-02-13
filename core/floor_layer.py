from core.region_base import LiquidRegion


class FloorLayer:
    def __init__(self, elevation, bg_color):
        self.elevation = elevation
        self.bg_color = bg_color
        self.floor_regions = []
        self.wall_regions = []

    def add_floor_region(self, region):
        self.floor_regions.append(region)

    def add_wall_region(self, region):
        self.wall_regions.append(region)

    def get_solid_regions(self):
        return [r for r in self.wall_regions if r.solid] + \
               [r for r in self.floor_regions if r.solid]

    def get_effect_regions(self):
        return [r for r in self.floor_regions if isinstance(r, LiquidRegion)]
