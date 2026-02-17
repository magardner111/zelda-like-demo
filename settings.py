# Window
WIDTH = 960
HEIGHT = 800
FPS = 60

# Background
BACKGROUND_COLOR = (0, 0, 0)

# Debug
DEBUG = False

# Edge Sliding (LTTP-style ledge mechanics)
EDGE_SLIDE_THRESHOLD = 0.7   # Test radius ratio; slide starts when any sample point
                              # at radius * threshold from center is over void
EDGE_SLIDE_ACCEL = 180       # Slide acceleration (px/sec²)
EDGE_SLIDE_MAX_SPEED = 400   # Max slide speed (px/sec)
