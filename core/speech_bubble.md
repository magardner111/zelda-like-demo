# Speech Bubble System

Word-by-word speech bubbles rendered above any `GameObject` (enemies, player, NPCs).

## Basic Usage

Call `say()` with a list of strings. Each string is one *page*: words appear
one at a time, then the completed page lingers before the next page begins.

```python
enemy.say(["Hello adventurer!", "Watch out for traps."])
player.say(["I found a key!"])
```

## Defaults

| Property        | Default            | Description                              |
|-----------------|--------------------|------------------------------------------|
| `word_interval` | `0.75` s/word      | Time between each word appearing         |
| `duration`      | `3.0` s            | How long the completed page stays on screen |
| `color`         | `(255, 255, 255)`  | Text colour (white)                      |
| `rows`          | `2`                | Max display rows                         |
| `cols`          | `32`               | Max display columns (characters)         |
| `font_size`     | `14`               | Font size in pixels                      |

## Per-Character Configuration

Override `self._speech` in a subclass `__init__` (after `super().__init__()`)
to give a character its own voice:

```python
class BossEnemy(Enemy):
    def __init__(self, position, stats):
        super().__init__(position, stats)
        self._speech = SpeechBubble(
            word_interval=1.2,
            color=(200, 50, 50),
            duration=4.0,
        )
```

## Markup

Markup tags can be embedded anywhere in a speech string.

| Tag             | Effect                                          |
|-----------------|-------------------------------------------------|
| `[pause:N]`     | Silence for N seconds before the next word      |
| `[slow]`        | Double the word interval                        |
| `[fast]`        | Halve the word interval                         |
| `[speed:N]`     | Set word interval to N seconds                  |
| `[/slow]`       | Restore default word interval (alias `[/speed]`)|
| `[/speed]`      | Restore default word interval                   |
| `[color:R,G,B]` | Change text colour (0–255 per channel)          |
| `[/color]`      | Restore default text colour                     |

### Example

```python
enemy.say([
    "[slow] Who... goes... [/slow] there?",
    "[pause:1.0] [color:255,100,100] ANSWER ME! [/color]",
])
```

## Overflow

Words that exceed the `rows × cols` display area are silently dropped.
Keep speech strings short, or increase `rows`/`cols` for chatty characters.
