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

    def point_on_floor(self, px, py):
        """Check if a single point is inside any floor or wall region rect."""
        for region in self.floor_regions:
            if region.rect.collidepoint(px, py):
                return True
        for region in self.wall_regions:
            if region.rect.collidepoint(px, py):
                return True
        return False

    def has_floor_at(self, pos, radius):
        """Check if any floor or wall region overlaps the given circle."""
        for region in self.floor_regions:
            if region.overlaps_circle(pos, radius):
                return True
        for region in self.wall_regions:
            if region.overlaps_circle(pos, radius):
                return True
        return False
