import pygame


class HudElement:
    """Base class for all HUD elements.

    position: (x, y) relative to parent container (or screen if no parent).
    size: (width, height) of this element.
    """

    def __init__(self, position=(0, 0), size=(0, 0)):
        self.rel_pos = pygame.Vector2(position)
        self.size = pygame.Vector2(size)
        self.visible = True

    def get_rect(self, parent_offset=(0, 0)):
        abs_pos = self.rel_pos + pygame.Vector2(parent_offset)
        return pygame.Rect(abs_pos, self.size)

    def update(self):
        pass

    def draw(self, screen, parent_offset=(0, 0)):
        pass


class HudBar(HudElement):
    """A bar that displays a ratio of current/max from callable data sources.

    value_source: callable returning current value
    max_source:   callable returning max value
    bar_color:    fill color of the bar
    bg_color:     background color behind the bar
    border_color: optional border color (None = no border)
    border_width: border thickness in pixels
    """

    def __init__(self, position=(0, 0), size=(200, 20),
                 value_source=None, max_source=None,
                 bar_color=(220, 50, 50), bg_color=(60, 60, 60),
                 border_color=None, border_width=1):
        super().__init__(position, size)
        self.value_source = value_source or (lambda: 0)
        self.max_source = max_source or (lambda: 1)
        self.bar_color = bar_color
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width

    def get_ratio(self):
        max_val = self.max_source()
        if max_val <= 0:
            return 0.0
        return max(0.0, min(1.0, self.value_source() / max_val))

    def draw(self, screen, parent_offset=(0, 0)):
        if not self.visible:
            return
        rect = self.get_rect(parent_offset)

        # Background
        pygame.draw.rect(screen, self.bg_color, rect)

        # Filled portion
        fill_width = int(rect.width * self.get_ratio())
        if fill_width > 0:
            fill_rect = pygame.Rect(rect.x, rect.y, fill_width, rect.height)
            pygame.draw.rect(screen, self.bar_color, fill_rect)

        # Border
        if self.border_color:
            pygame.draw.rect(screen, self.border_color, rect, self.border_width)


class HudText(HudElement):
    """A text label, optionally bound to a data source.

    text_source: callable returning a string, OR None to use static text.
    text:        static text (used when text_source is None).
    """

    def __init__(self, position=(0, 0), text="", text_source=None,
                 color=(255, 255, 255), font_size=24):
        self._font = pygame.font.SysFont(None, font_size)
        # Estimate size from static text for layout purposes
        surface = self._font.render(text or "X", True, color)
        super().__init__(position, (surface.get_width(), surface.get_height()))
        self.text = text
        self.text_source = text_source
        self.color = color

    def draw(self, screen, parent_offset=(0, 0)):
        if not self.visible:
            return
        display_text = self.text_source() if self.text_source else self.text
        surface = self._font.render(display_text, True, self.color)
        pos = self.rel_pos + pygame.Vector2(parent_offset)
        screen.blit(surface, pos)


class HudContainer(HudElement):
    """A rectangular region that holds child HudElements.

    Children are positioned relative to this container's top-left corner.
    bg_color: (r, g, b, a) tuple — use alpha for transparency.
    """

    def __init__(self, position=(0, 0), size=(100, 100),
                 bg_color=(0, 0, 0, 120)):
        super().__init__(position, size)
        self.bg_color = bg_color
        self.children = []

    def add(self, element):
        self.children.append(element)
        return element

    def update(self):
        for child in self.children:
            child.update()

    def draw(self, screen, parent_offset=(0, 0)):
        if not self.visible:
            return
        rect = self.get_rect(parent_offset)

        # Draw background with alpha support
        if len(self.bg_color) == 4:
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            surf.fill(self.bg_color)
            screen.blit(surf, (rect.x, rect.y))
        else:
            pygame.draw.rect(screen, self.bg_color, rect)

        # Draw children relative to this container's absolute position
        child_offset = (rect.x, rect.y)
        for child in self.children:
            child.draw(screen, child_offset)


class HudLayer:
    """Top-level manager that holds containers/elements and draws them all."""

    def __init__(self):
        self.elements = []

    def add(self, element):
        self.elements.append(element)
        return element

    def update(self):
        for element in self.elements:
            element.update()

    def draw(self, screen):
        for element in self.elements:
            element.draw(screen)
