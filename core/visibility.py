import math


def compute_visibility_polygon(player_pos, wall_rects, map_width, map_height):
    """Cast rays from player_pos toward wall corners to build a visibility polygon.

    Returns a list of (x, y) points sorted by angle, forming the visible area.
    """
    px, py = player_pos

    # Collect wall segments — backface culling: only add faces that face toward
    # the player.  Back-facing segments are never the closest ray hit for an
    # external player position (the front face is always closer), so they add
    # only wasted work.  This halves both segment count and corner/ray count,
    # giving ~4x speedup in the inner O(rays × segments) loop.
    segments = []
    points = set()
    for r in wall_rects:
        x, y, w, h = r.x, r.y, r.width, r.height
        x2, y2 = x + w, y + h
        if py <= y:        # player above → top face
            segments.append(((x, y), (x2, y)))
            points.add((x, y)); points.add((x2, y))
        if py >= y2:       # player below → bottom face
            segments.append(((x, y2), (x2, y2)))
            points.add((x, y2)); points.add((x2, y2))
        if px <= x:        # player left → left face
            segments.append(((x, y), (x, y2)))
            points.add((x, y)); points.add((x, y2))
        if px >= x2:       # player right → right face
            segments.append(((x2, y), (x2, y2)))
            points.add((x2, y)); points.add((x2, y2))

    # Map boundary segments
    boundary_corners = [(0, 0), (map_width, 0), (map_width, map_height), (0, map_height)]
    for i in range(4):
        segments.append((boundary_corners[i], boundary_corners[(i + 1) % 4]))
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
