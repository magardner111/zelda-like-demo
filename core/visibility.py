import math
import numpy as np


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

    if not segments:
        return []

    # Build segment arrays: shape (N_segs,)
    seg_arr = np.array(segments, dtype=np.float64)  # (N_segs, 2, 2)
    ax = seg_arr[:, 0, 0]
    ay = seg_arr[:, 0, 1]
    sdx = seg_arr[:, 1, 0] - ax  # segment direction x
    sdy = seg_arr[:, 1, 1] - ay  # segment direction y

    # Cast rays: for each corner, cast 3 rays (corner angle +/- tiny offset)
    epsilon = 0.0001
    ray_angles = []
    for (cx, cy) in points:
        angle = math.atan2(cy - py, cx - px)
        ray_angles.extend([angle - epsilon, angle, angle + epsilon])

    ray_angles = np.array(ray_angles, dtype=np.float64)
    rdx = np.cos(ray_angles)  # (N_rays,)
    rdy = np.sin(ray_angles)  # (N_rays,)

    # Vectorized ray-segment intersection via broadcasting: (N_rays, N_segs)
    # denom = rdx * sdy - rdy * sdx
    denom = rdx[:, np.newaxis] * sdy[np.newaxis, :] - rdy[:, np.newaxis] * sdx[np.newaxis, :]

    # Offsets from ray origin to each segment start
    dx = ax[np.newaxis, :] - px  # broadcasts to (N_rays, N_segs)
    dy = ay[np.newaxis, :] - py

    # t = (dx * sdy - dy * sdx) / denom  — distance along ray
    # u = (dx * rdy - dy * rdx) / denom  — position along segment [0,1]
    t_num = dx * sdy[np.newaxis, :] - dy * sdx[np.newaxis, :]
    u_num = dx * rdy[:, np.newaxis] - dy * rdx[:, np.newaxis]

    # Avoid division by zero for near-parallel rays
    parallel = np.abs(denom) < 1e-10
    safe_denom = np.where(parallel, 1.0, denom)

    t = t_num / safe_denom
    u = u_num / safe_denom

    # Mask invalid hits: parallel, t < 0, u outside [0,1]
    t[parallel | (t < 0) | (u < 0) | (u > 1)] = np.inf

    # Nearest hit per ray
    closest_t = np.min(t, axis=1)  # (N_rays,)

    # Compute intersection points
    hit_x = px + rdx * closest_t
    hit_y = py + rdy * closest_t

    # Filter rays that hit nothing
    valid = np.isfinite(closest_t)
    valid_angles = ray_angles[valid]
    valid_x = hit_x[valid]
    valid_y = hit_y[valid]

    # Sort by angle and return polygon points
    sort_idx = np.argsort(valid_angles)
    return list(zip(valid_x[sort_idx].tolist(), valid_y[sort_idx].tolist()))


def point_in_polygon(x, y, polygon):
    """Ray-casting point-in-polygon test (numpy vectorized)."""
    poly = np.array(polygon, dtype=np.float64)
    xi = poly[:, 0]
    yi = poly[:, 1]
    xj = np.roll(xi, 1)
    yj = np.roll(yi, 1)

    # Edge crossing: yi and yj on opposite sides of y
    crossing = (yi > y) != (yj > y)
    # Safe division — when crossing is True, yj != yi is guaranteed
    dy = yj - yi
    safe_dy = np.where(dy == 0.0, 1.0, dy)
    x_intersect = (xj - xi) * (y - yi) / safe_dy + xi

    return int(np.sum(crossing & (x < x_intersect))) % 2 == 1
