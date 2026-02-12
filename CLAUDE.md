# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
pip install -r requirements.txt
python main.py
```

The only dependency is `pygame-ce` (Pygame Community Edition).

## Architecture

This is a Zelda-like action game demo built with Pygame CE. There is no build system, test framework, or CI.

### Game Loop (main.py)

Each frame follows: **Input → Update → Camera → Render**

1. `InputManager.update()` samples keyboard state
2. `Map.update()` ticks all enemies (pattern-based AI)
3. `Player.update()` handles movement, weapon attacks, and damage
4. `Camera.update()` processes screen shake
5. Everything renders with camera offset applied

### Module Relationships

- **core/** — Player, Enemy base class, InputManager, Camera. Player owns weapons via `add_weapon()` composition.
- **weapons/** — Weapon implementations attached to Player. `Sword` handles its own collision detection against enemies. `bow.py` is a stub.
- **enemies/** — Concrete enemy types extending `Enemy`. Each enemy is assigned a behavior pattern.
- **patterns/** — State-machine behavior patterns (e.g., `UpDownPattern`) that drive enemy movement.
- **maps/** — `MapBase` manages a list of enemies. Concrete maps (e.g., `Lvl1Map`) populate enemies on init.
- **data/** — Pure data dictionaries (`PLAYER_STATS`, `ENEMY_STATS`, `SWORD_STATS`) consumed by entity constructors.
- **settings.py** — Global constants: screen dimensions (960×800), FPS (60), background color.

### Key Design Patterns

- **Data-driven entities**: Stats are defined in `data/` dicts and passed to constructors, not hardcoded in classes.
- **Pattern-based enemy AI**: Enemies delegate movement to pattern objects with state machines (e.g., move → pause → move).
- **Weapon composition**: Weapons are stored in `Player.weapons` dict, updated/drawn via the player, but handle their own attack logic and collision.
- **Input abstraction**: `InputManager` maps keys to action names with `is_down()`, `is_pressed()`, `is_released()` for hold/edge detection.

### Stubs (not yet implemented)

`core/collision.py`, `core/pattern_base.py` (minimal), `weapons/bow.py` are empty or minimal placeholders.
