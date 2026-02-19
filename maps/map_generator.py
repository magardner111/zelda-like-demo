import random

from core.floor_layer import FloorLayer
from core.region_base import FloorRegion, WallRegion
from data.region_stats import REGION_STATS
from maps.layout import Layout, get_direction
from maps.map_base import MapBase

ROOM_SIZE = 800
WALL_THICKNESS = 32
DOOR_WIDTH = 64

_DOOR_OFFSET = (ROOM_SIZE - DOOR_WIDTH) // 2   # 368 — gap starts here
_LAYER_BG = (30, 30, 35)


# ---------------------------------------------------------------------------
# Internal helpers — yield absolute pixel rects for wall segments
# ---------------------------------------------------------------------------

def _hwall_rects(rx, ry, has_door):
    """Horizontal wall row at (rx, ry), ROOM_SIZE wide, WALL_THICKNESS tall.
    Splits around a centred DOOR_WIDTH gap when has_door is True.
    """
    if not has_door:
        yield (rx, ry, ROOM_SIZE, WALL_THICKNESS)
    else:
        yield (rx,                          ry, _DOOR_OFFSET,                       WALL_THICKNESS)
        yield (rx + _DOOR_OFFSET + DOOR_WIDTH, ry, ROOM_SIZE - _DOOR_OFFSET - DOOR_WIDTH, WALL_THICKNESS)


def _vwall_rects(rx, ry, has_door):
    """Vertical wall column at (rx, ry), WALL_THICKNESS wide, ROOM_SIZE tall.
    Splits around a centred DOOR_WIDTH gap when has_door is True.
    """
    if not has_door:
        yield (rx, ry, WALL_THICKNESS, ROOM_SIZE)
    else:
        yield (rx, ry,                          WALL_THICKNESS, _DOOR_OFFSET)
        yield (rx, ry + _DOOR_OFFSET + DOOR_WIDTH, WALL_THICKNESS, ROOM_SIZE - _DOOR_OFFSET - DOOR_WIDTH)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_map(layout: Layout):
    """Build a MapBase from a Layout.

    Every room becomes an 800×800 pixel cell with stone floor and 32-pixel
    thick walls.  Rooms are placed so adjacent grid cells share a wall edge.
    Where two rooms are connected by a corridor, a 64-pixel-wide centred
    doorway is cut in both facing walls.

    Returns
    -------
    map_obj : MapBase
    player_start : (int, int)
        Pixel centre of room 0 — use this as the player's initial position.
    """
    if layout.seed is not None:
        random.seed(layout.seed)

    # --- normalise grid positions so top-left room starts at pixel (0, 0) ---
    all_pos  = [layout.get_pos(n) for n in layout.rooms()]
    min_gx   = min(p[0] for p in all_pos)
    min_gy   = min(p[1] for p in all_pos)
    max_gx   = max(p[0] for p in all_pos)
    max_gy   = max(p[1] for p in all_pos)

    total_w  = (max_gx - min_gx + 1) * ROOM_SIZE
    total_h  = (max_gy - min_gy + 1) * ROOM_SIZE

    def room_origin(gx, gy):
        return ((gx - min_gx) * ROOM_SIZE, (gy - min_gy) * ROOM_SIZE)

    # --- build map skeleton ---
    map_obj = MapBase(width=total_w, height=total_h)
    layer   = FloorLayer(elevation=0, bg_color=_LAYER_BG)
    map_obj.add_layer(layer)

    wall_stats  = REGION_STATS["wall"]
    floor_stats = REGION_STATS["stone"]

    # --- place each room ---
    for room_id in layout.rooms():
        gx, gy   = layout.get_pos(room_id)
        rx, ry   = room_origin(gx, gy)

        # Which cardinal directions have a corridor to a neighbour?
        # get_direction uses the layout's convention:
        #   "east"  dx=+1  → right wall   (x = rx + ROOM_SIZE - WALL_THICKNESS)
        #   "west"  dx=-1  → left wall    (x = rx)
        #   "north" dy=+1  → bottom wall  (y = ry + ROOM_SIZE - WALL_THICKNESS)
        #                     (y increases downward in screen space)
        #   "south" dy=-1  → top wall     (y = ry)
        open_dirs = set()
        for nbr in layout.neighbors(room_id):
            ngx, ngy = layout.get_pos(nbr)
            d = get_direction((gx, gy), (ngx, ngy))
            if d:
                open_dirs.add(d)

        # floor — full room
        layer.add_floor_region(
            FloorRegion((rx, ry, ROOM_SIZE, ROOM_SIZE), "stone", floor_stats)
        )

        # top wall    ("south" neighbour is above in screen space)
        for rect in _hwall_rects(rx, ry, "south" in open_dirs):
            layer.add_wall_region(WallRegion(rect, wall_stats))

        # bottom wall ("north" neighbour is below in screen space)
        for rect in _hwall_rects(rx, ry + ROOM_SIZE - WALL_THICKNESS, "north" in open_dirs):
            layer.add_wall_region(WallRegion(rect, wall_stats))

        # left wall
        for rect in _vwall_rects(rx, ry, "west" in open_dirs):
            layer.add_wall_region(WallRegion(rect, wall_stats))

        # right wall
        for rect in _vwall_rects(rx + ROOM_SIZE - WALL_THICKNESS, ry, "east" in open_dirs):
            layer.add_wall_region(WallRegion(rect, wall_stats))

    # --- player start: centre of room 0 ---
    r0x, r0y    = room_origin(*layout.get_pos(0))
    player_start = (r0x + ROOM_SIZE // 2, r0y + ROOM_SIZE // 2)

    return map_obj, player_start
