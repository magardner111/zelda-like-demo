import math
import re

import pygame

# Matches [tag], [tag:value], [/tag]
_MARKUP_RE = re.compile(r'\[(/?\w+)(?::([^\]]*))?\]')


def _tokenize(text):
    """Split *text* into ('word', str) and ('markup', tag, val) tuples."""
    tokens = []
    pos = 0
    for m in _MARKUP_RE.finditer(text):
        for w in text[pos:m.start()].split():
            tokens.append(('word', w))
        tokens.append(('markup', m.group(1).lower(), m.group(2)))
        pos = m.end()
    for w in text[pos:].split():
        tokens.append(('word', w))
    return tokens


class SpeechBubble:
    """Word-by-word speech bubble rendered above a game entity.

    Each string passed to :meth:`say` is one *page*: words appear one at a
    time at *word_interval* seconds each, then the completed page lingers for
    *duration* seconds before the next page begins.

    Markup tokens (embedded anywhere in a speech string)
    ----------------------------------------------------
    [pause:N]     add N seconds of silence before the next word
    [speed:N]     set seconds-per-word to N for subsequent words
    [slow]        double the word interval (half-speed)
    [fast]        halve the word interval (double-speed)
    [/speed]      restore the default word interval
    [/slow]       alias for [/speed]
    [color:R,G,B] set word colour for subsequent words (0-255 each channel)
    [/color]      restore the default colour
    """

    def __init__(
        self,
        word_interval: float = 0.75,
        duration: float = 3.0,
        color=(255, 255, 255),
        rows: int = 2,
        cols: int = 32,
        font_size: int = 14,
    ):
        self._default_interval = word_interval
        self._default_color = color
        self.duration = duration
        self.rows = rows
        self.cols = cols
        self.font_size = font_size
        self._font = None  # lazy init — pygame.font must be ready first

        # Smoothed world-space position — lerps toward the entity each update
        # so the bubble glides rather than snapping to every pixel of movement.
        self._smoothed_pos = None   # pygame.Vector2 or None until first update

        self._queue = []        # strings waiting to be displayed
        self._state = 'idle'    # 'idle' | 'typing' | 'hold'

        # Current page state
        self._lines = []        # list[list[(word, color)]] — filled rows
        self._schedule = []     # list[(delay, word, color)] — word events
        self._sched_idx = 0
        self._sched_timer = 0.0
        self._hold_timer = 0.0
        self._cur_row = 0
        self._cur_col = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def say(self, strings):
        """Queue *strings* for word-by-word display.

        If already displaying, the new pages are appended after any already
        queued.  Pass a single-element list to show one page.
        """
        self._queue.extend(strings)
        if self._state == 'idle':
            self._advance()

    @property
    def is_active(self):
        """True while any text is being displayed or queued."""
        return self._state != 'idle'

    # ------------------------------------------------------------------
    # Update / Draw
    # ------------------------------------------------------------------

    def update(self, dt, entity_pos=None):
        # Smooth the display position toward the entity's current world position.
        # Using an exponential lerp (frame-rate independent) with rate=15:
        #   steady-state lag ≈ velocity / rate  (e.g. 350 px/s → ~23 px lag)
        # This removes per-frame jitter while keeping the bubble close.
        if entity_pos is not None:
            target = pygame.Vector2(entity_pos)
            if self._smoothed_pos is None:
                self._smoothed_pos = target.copy()
            else:
                t = 1.0 - math.exp(-15.0 * dt)
                self._smoothed_pos += (target - self._smoothed_pos) * t

        if self._state == 'idle':
            return

        if self._state == 'typing':
            self._sched_timer += dt
            while self._sched_idx < len(self._schedule):
                delay, word, color = self._schedule[self._sched_idx]
                if self._sched_timer < delay:
                    break
                self._sched_timer -= delay
                self._place_word(word, color)
                self._sched_idx += 1
            if self._sched_idx >= len(self._schedule):
                self._state = 'hold'
                self._hold_timer = self.duration

        elif self._state == 'hold':
            self._hold_timer -= dt
            if self._hold_timer <= 0.0:
                self._advance()

    def draw(self, screen, camera, world_pos, visual_radius):
        """Draw the speech bubble above the entity.

        Parameters
        ----------
        camera        : camera object with an apply(pos) method.
        world_pos     : (x, y) centre of the entity in world coordinates.
        visual_radius : entity pixel half-size; pushes the bubble upward.
        """
        if self._state == 'idle':
            return

        if self._font is None:
            self._font = pygame.font.SysFont('monospace', self.font_size)

        # Render from the smoothed world position so the bubble glides smoothly.
        # Fall back to the raw world_pos if smoothing hasn't started yet.
        render_pos = self._smoothed_pos if self._smoothed_pos is not None \
            else pygame.Vector2(world_pos)
        screen_pos = camera.apply(render_pos)

        char_w = self._font.size('M')[0]
        line_h = self._font.get_linesize()
        pad = 6

        bubble_w = self.cols * char_w + pad * 2
        bubble_h = self.rows * line_h + pad * 2

        cx, cy = screen_pos[0], screen_pos[1]
        bx = cx - bubble_w // 2
        by = cy - visual_radius - bubble_h - 8

        # Snap to whole pixels for crisp rendering
        bx, by = int(bx), int(by)

        # Background + border
        bg = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)
        bg.fill((20, 20, 20, 180))
        screen.blit(bg, (bx, by))
        pygame.draw.rect(screen, (160, 160, 160), (bx, by, bubble_w, bubble_h), 1)

        # Text rows
        for row_idx, line in enumerate(self._lines):
            x = bx + pad
            y = by + pad + row_idx * line_h
            for i, (word, color) in enumerate(line):
                if i > 0:
                    x += self._font.size(' ')[0]
                surf = self._font.render(word, True, color)
                screen.blit(surf, (x, y))
                x += surf.get_width()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _advance(self):
        if not self._queue:
            self._state = 'idle'
            return
        text = self._queue.pop(0)
        self._lines = [[] for _ in range(self.rows)]
        self._cur_row = 0
        self._cur_col = 0
        self._schedule = self._build_schedule(text)
        self._sched_idx = 0
        self._sched_timer = 0.0
        if self._schedule:
            self._state = 'typing'
        else:
            self._state = 'hold'
            self._hold_timer = self.duration

    def _build_schedule(self, text):
        """Parse *text* with markup into a list of (delay, word, color) events."""
        tokens = _tokenize(text)
        schedule = []
        interval = self._default_interval
        color = self._default_color
        pending_extra = 0.0

        for tok in tokens:
            kind = tok[0]
            if kind == 'word':
                schedule.append((interval + pending_extra, tok[1], color))
                pending_extra = 0.0
            elif kind == 'markup':
                _, tag, val = tok
                if tag == 'pause':
                    try:
                        pending_extra += float(val)
                    except (TypeError, ValueError):
                        pass
                elif tag == 'speed':
                    try:
                        interval = float(val)
                    except (TypeError, ValueError):
                        pass
                elif tag in ('/speed', '/slow'):
                    interval = self._default_interval
                elif tag == 'slow':
                    interval = self._default_interval * 2.0
                elif tag == 'fast':
                    interval = self._default_interval * 0.5
                elif tag == 'color':
                    try:
                        r, g, b = [int(x.strip()) for x in val.split(',')]
                        color = (r, g, b)
                    except (TypeError, ValueError, AttributeError):
                        pass
                elif tag == '/color':
                    color = self._default_color
        return schedule

    def _place_word(self, word, color):
        """Place *word* into the display grid, wrapping to the next row if needed."""
        if self._cur_row >= self.rows:
            return  # display full — drop overflow
        line = self._lines[self._cur_row]
        leading = 1 if line else 0
        needed = leading + len(word)
        if self._cur_col + needed <= self.cols:
            line.append((word, color))
            self._cur_col += needed
        else:
            self._cur_row += 1
            if self._cur_row >= self.rows:
                return  # overflow
            self._lines[self._cur_row].append((word, color))
            self._cur_col = len(word)
