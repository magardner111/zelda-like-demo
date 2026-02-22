import pygame


class Explosion:
    """Generic explosion effect.

    Immediately damages all entities on the same layer within *radius* pixels,
    then plays a short visual (bright flash + expanding ring).

    Parameters
    ----------
    pos : pygame.Vector2 | tuple
        World-space centre of the explosion.
    layer : int
        Floor-layer elevation; only entities on this layer are damaged.
    entities : iterable
        Any iterable of game objects that may have ``take_damage()``.
    radius : float
        Damage + visual radius in pixels.
    damage : int
        Hit-points removed from each qualifying entity.
    duration : float
        How long (seconds) the visual plays before ``done`` is set True.
    shake : tuple | None
        ``(duration, intensity)`` forwarded to ``camera.shake()``.
        Drained by main.py on the frame the explosion is created.
        Pass ``None`` to suppress camera shake.
    """

    def __init__(self, pos, layer, entities,
                 radius=80, damage=3, duration=0.5, shake=(0.25, 20)):
        self.pos = pygame.Vector2(pos)
        self.layer = layer
        self.radius = radius
        self.duration = duration
        self.done = False
        self._timer = 0.0
        self._pending_shake = shake

        # Apply damage immediately to all qualifying entities
        for entity in entities:
            if getattr(entity, 'current_layer', layer) != layer:
                continue
            if not hasattr(entity, 'take_damage'):
                continue
            entity_pos = getattr(entity, 'pos', None)
            if entity_pos is None:
                continue
            if (entity_pos - self.pos).length() <= radius:
                entity.take_damage(damage, self.pos, knockback=400)

    # ------------------------------------------------------------------

    def update(self, dt):
        self._timer += dt
        if self._timer >= self.duration:
            self.done = True

    def draw(self, screen, camera):
        t = min(self._timer / self.duration, 1.0)   # 0 → 1 over lifetime

        ox, oy = int(camera.offset.x), int(camera.offset.y)
        cx = int(self.pos.x) + ox
        cy = int(self.pos.y) + oy
        r = int(self.radius)

        # --- Flash layer: bright white/yellow circle, fades in first 30% ---
        flash_t = t / 0.3  # 0→1 over first 30% of duration
        if flash_t < 1.0:
            flash_alpha = int(220 * (1.0 - flash_t))
            flash_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            # Interpolate from white → yellow
            col = (255, int(255 * (0.8 + 0.2 * flash_t)), 0, flash_alpha)
            pygame.draw.circle(flash_surf, col, (r, r), r)
            screen.blit(flash_surf, (cx - r, cy - r))

        # --- Ring layer: orange outline, grows 0 → radius, fades to 0 ---
        ring_r = int(r * t)
        ring_alpha = int(255 * (1.0 - t))
        if ring_r >= 1 and ring_alpha > 0:
            ring_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
            ring_col = (255, 140, 0, ring_alpha)
            pygame.draw.circle(ring_surf, ring_col,
                               (ring_r + 2, ring_r + 2), ring_r, 4)
            screen.blit(ring_surf, (cx - ring_r - 2, cy - ring_r - 2))
