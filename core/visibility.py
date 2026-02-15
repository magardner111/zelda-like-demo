import math


def compute_visibility_polygon(player_pos, wall_rects, map_width, map_height):
    """Cast rays from player_pos toward wall corners to build a visibility polygon.

    Returns a list of (x, y) points sorted by angle, forming the visible area.
    """
    px, py = player_pos

    # Collect all wall segments
    segments = []
    for r in wall_rects:
        x, y, w, h = r.x, r.y, r.width, r.height
        corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        for i in range(4):
            segments.append((corners[i], corners[(i + 1) % 4]))

    # Map boundary segments
    boundary_corners = [(0, 0), (map_width, 0), (map_width, map_height), (0, map_height)]
    for i in range(4):
        segments.append((boundary_corners[i], boundary_corners[(i + 1) % 4]))

    # Collect unique corner points to cast rays toward
    points = set()
    for r in wall_rects:
        x, y, w, h = r.x, r.y, r.width, r.height
        points.update([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    points.update(boundary_corners)

    # Cast rays: for each corner, cast 3 rays (corner angle ± tiny offset)
    epsilon = 0.0001
    ray_angles = []
    for (cx, cy) in points:
        angle = math.atan2(cy - py, cx - px)
        ray_angles.extend([angle - epsilon, angle, angle + epsilon])

    # For each ray angle, find the nearest intersection
    intersections = []
    for angle in ray_angles:
        rdx = math.cos(angle)
        rdy = math.sin(angle)

        closest_t = float("inf")
        closest_point = None

        for (ax, ay), (bx, by) in segments:
            hit = _ray_segment_intersect(px, py, rdx, rdy, ax, ay, bx, by)
            if hit is not None:
                t, ix, iy = hit
                if t < closest_t:
                    closest_t = t
                    closest_point = (ix, iy)

        if closest_point is not None:
            intersections.append((angle, closest_point))

    # Sort by angle and return the polygon points
    intersections.sort(key=lambda item: item[0])
    return [pt for _, pt in intersections]


def point_in_polygon(x, y, polygon):
    """Ray-casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _ray_segment_intersect(px, py, rdx, rdy, ax, ay, bx, by):
    """Intersect ray (px,py)+t*(rdx,rdy) with segment (ax,ay)-(bx,by).

    Returns (t, ix, iy) or None.
    """
    sdx = bx - ax
    sdy = by - ay

    denom = rdx * sdy - rdy * sdx
    if abs(denom) < 1e-10:
        return None

    t = ((ax - px) * sdy - (ay - py) * sdx) / denom
    u = ((ax - px) * rdy - (ay - py) * rdx) / denom

    if t >= 0 and 0 <= u <= 1:
        return (t, px + rdx * t, py + rdy * t)
    return None
