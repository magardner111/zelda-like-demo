import math
import random

import pygame

from core.enemy_base import Enemy, _line_clear
from core.speech_bubble import SpeechBubble
from enemies.rock import Rock
from patterns.enemy_patterns import KeepDistancePattern, KamikazePattern

# ---------------------------------------------------------------------------
# Quip library
# ---------------------------------------------------------------------------

_QUIPS = [
    # Unhinged mod authority
    "I AM A MODERATOR AND YOU WILL SHOW SOME FUCKING RESPECT!!",
    "DO YOU HAVE ANY IDEA HOW LONG I HAVE BEEN A MOD?! NINE YEARS!! NINE!!",
    "I HAVE THE POWER TO BAN YOU AND I AM NOT AFRAID TO USE IT!!",
    "THIS IS MY DUNGEON!! MINE!! I BUILT THIS COMMUNITY FROM NOTHING!!",
    "YOU ARE IN VIOLATION OF RULE FOUR!! RULE! FOUR!!",
    "I AM GOING TO REPORT THIS TO THE ADMINS AND THEY WILL HEAR ME!!",
    "THE MOD TEAM HAS BEEN NOTIFIED!! ALL THREE OF US!!",
    "I DO THIS FOR FREE!! FOR FREE!! AND THIS IS HOW YOU TREAT ME?!",
    "I HAVE CONTACTED SUPPORT!! I AM ON HOLD RIGHT NOW!! SCREAMING!!",
    "THIS HAS BEEN LOGGED!! EVERYTHING IS LOGGED!! I LOG EVERYTHING!!",
    "YOU THINK YOU CAN JUST WALK AROUND MY DUNGEON?! THINK AGAIN ASSHOLE!!",
    "I AM LITERALLY SHAKING RIGHT NOW!! DO YOU UNDERSTAND THAT?! SHAKING!!",

    # Crying while angry
    "I am NOT crying!! [pause:0.5] These are RAGE TEARS!! There's a DIFFERENCE!!",
    "I'M FINE!! [pause:0.4] I AM COMPLETELY FINE!! STOP LOOKING AT ME!!",
    "You have made me so angry I can't even TYPE properly and I'm not even typing!!",
    "My HANDS are SHAKING!! Look at them!! [pause:0.5] Don't look at them!!",
    "I just need a MINUTE!! [pause:0.6] I DON'T NEED A MINUTE!! COME BACK HERE!!",
    "[slow] I am so... [/slow] UNBELIEVABLY FUCKING ANGRY RIGHT NOW!!",
    "I am going to go calm down. [pause:0.4] I AM NOT CALM!! I LIED!!",
    "Do you see what you've DONE?! I was FINE before you showed up!! FINE!!",

    # Threatening bans and consequences
    "Say goodbye to your posting privileges you absolute shit!!",
    "I will shadowban you so fast your head will fucking spin off!!",
    "You are going to REGRET this!! I have a very long memory!!",
    "I am going to write a post about you!! A DETAILED post!! With SCREENSHOTS!!",
    "I know people!! I know ADMINS!! I have their PERSONAL EMAILS!!",
    "This is a permanent record and yours is DISGUSTING right now!!",
    "You think this is over?! This is NOT over!! I have DMs to send!!",

    # Intelligence / superiority meltdown
    "I have a HUNDRED AND SEVENTY IQ and you're making ME feel stupid?! HOW?!",
    "WELL ACTUALLY— [pause:0.4] SHUT UP I'M TALKING!! WELL ACTUALLY!!",
    "I wrote the WIKI!! THE WHOLE THING!! DO YOUR RESEARCH YOU IGNORANT SHIT!!",
    "My SOURCES are IMPECCABLE!! Do you even HAVE sources?! I have SEVENTEEN!!",
    "You wouldn't UNDERSTAND because you haven't READ anything!! EVER!!",
    "I have a CERTIFICATE!! A REAL ONE!! FRAMED!! ON MY WALL!!",
    "This has been addressed in the MEGATHREAD you LAZY PIECE OF SHIT!!",

    # Proximity freakout
    "GET AWAY FROM ME!! BACK UP!! YOU'RE TOO CLOSE!! BACK THE FUCK UP!!",
    "WHY ARE YOU SO CLOSE?! THIS IS A VIOLATION!! A LITERAL VIOLATION!!",
    "I CAN SMELL YOU AND IT IS NOT HELPING MY ANXIETY RIGHT NOW!!",
    "PERSONAL SPACE!! LOOK IT UP!! IT'S A THING THAT EXISTS!! BACK OFF!!",
    "DO NOT TOUCH ME!! DO NOT!! I WILL ESCALATE THIS IMMEDIATELY!!",

    # Basement / lifestyle rage
    "I AM PERFECTLY HAPPY DOWN HERE!! STOP IMPLYING THINGS!!",
    "I have not LEFT this dungeon in FOUR YEARS and I am THRIVING!! THRIVING!!",
    "My MOM supports my modding and she said I'm doing a GREAT JOB!! SO THERE!!",
    "The LIGHTING is FINE down here!! I LIKE IT!! LEAVE ME ALONE!!",
    "I showered!! [pause:0.4] RECENTLY!! Stop making that face!! I SHOWERED!!",

    # Nonsensical screaming
    "YOU ABSOLUTE SHIT-FLAVORED WEDNESDAY!! WHAT IS WRONG WITH YOU?!",
    "I AM SO FUCKING PERPENDICULAR TO YOU RIGHT NOW I CANNOT EXPLAIN IT!!",
    "YOU TREMENDOUS ASS-RECTANGLE!! COME BACK HERE SO I CAN BAN YOU!!",
    "WHAT IN THE BASTARD-ADJACENT HELL DO YOU THINK YOU'RE DOING?!",
    "YOU MOIST LITTLE SHIT-LAMP!! I AM LOGGING THIS!!",
    "I AM VIBRATING WITH RAGE!! ACTUAL VIBRATING!! FEEL THE FLOOR!!",
    "YOU ABSOLUTE SCROTUM-SHAPED TUESDAY!! I HAVE WARNED YOU!!",
    "WHAT THE FUCK-FLAVORED FUCK IS HAPPENING RIGHT NOW?! EXPLAIN!!",

    # Can't catch me but furious about it
    "YOU CAN'T BAN ME IF YOU CAN'T CATCH ME!! WHICH YOU CAN'T!! LOSER!!",
    "I AM FASTER THAN YOU AND I AM IN THE RIGHT!! BOTH THINGS ARE TRUE!!",
    "TRY TO CATCH ME!! [pause:0.4] HAHA!! [pause:0.3] I'M STILL LOGGING THIS!!",
    "COME BACK HERE SO I CAN FORMALLY WARN YOU TO YOUR FACE!!",
    "I COULD REPORT YOU RIGHT NOW!! HOW DOES THAT FEEL?! DOES IT FEEL BAD?!",
    "RUNNING AWAY DOESN'T MEAN YOU'RE NOT BANNED!! YOU'RE STILL BANNED!!",

    # REEEEE
    "REEEEEEEEEEE!!",
    "REEEEE!! [pause:0.5] REEEEEEEEE!!",
    "I— [pause:0.3] REEEEEEEEEEEEEEEE!!",
    "REEEE!! [pause:0.3] I MEAN— [pause:0.3] REEEEEEEEE!!",
    "YOU— [pause:0.2] HOW DARE— [pause:0.2] REEEEEEEEEEEEE!!",
    "I WAS GOING TO SAY SOMETHING INTELLIGENT BUT REEEEEEEEEEE!!",
    "REEEEE!! [pause:0.6] THIS IS NOT OVER!! REEEEEEEEE!!",
    "JUST— [pause:0.2] REEEEEEEEEEEEEEEEEEEEEEEEE!!",

    # Wheezing
    "hhhHHHH— [pause:0.4] wheeze— [pause:0.3] I AM SO ANGRY RIGHT NOW!!",
    "*wheeze* [pause:0.5] I'M FINE!! [pause:0.3] *wheeze* [pause:0.4] BANNED!!",
    "You— [pause:0.3] *wheeze* [pause:0.4] I— [pause:0.3] REEEEEEE!!",
    "*wheeze* [pause:0.5] *wheeze* [pause:0.4] THIS IS HARASSMENT!!",
    "I'm not out of breath!! [pause:0.4] *wheeze* [pause:0.3] YOU'RE out of breath!!",
    "*wheeze* [pause:0.6] The report has been submitted. *wheeze*",
    "COME BACK— [pause:0.3] *wheeze* [pause:0.5] REEEEEEE— [pause:0.3] *wheeze*",
    "*wheeze* [pause:0.4] I have been running for thirty seconds!! *wheeze* [pause:0.3] Worth it!!",
]


_ENRAGE_QUIPS = [
    # Named final attacks — DBZ power-up energy
    "FINAL ATTACK: MODERATOR EXTINCTION BEAM!! THIS IS MY ULTIMATE TECHNIQUE!! REEEEEEEEE!!",
    "I AM POWERING BEYOND MY LIMITS!! SPECIAL MOVE: BANHAMMER SUPERNOVA!! REEEEEEEEE!!",
    "ULTIMATE TECHNIQUE UNLOCKED!! IT IS CALLED... RULE FOUR ANNIHILATION!! REEEEEEEEEEE!!",
    "HEAR THE NAME OF MY FINAL ATTACK!! IT IS: NINE-YEAR GRUDGE IMPACT!! REEEEEEEEEEE!!",
    "THIS POWER CANNOT BE STOPPED!! FINAL FORM: WIKI OBLITERATION OMEGA!! REEEEEEEEE!!",
    "SPECIAL MOVE: LOG ENTRY NUMBER INFINITY!! THIS IS MY STRONGEST ATTACK!! REEEEEEEEE!!",
    "I TRAINED NINE YEARS IN THIS DUNGEON FOR THIS MOMENT!! MODERATOR'S REQUIEM!! REEEEEEE!!",
    "BEYOND PLUS ULTRA!! WAIT WRONG SHOW!! DOESN'T MATTER!! CERTIFICATION DESTRUCTION FINAL!! REEEEEEE!!",
    "FINAL TECHNIQUE: THE COMPLETE PERMANENT RECORD!! ALL OF IT!! AT ONCE!! REEEEEEEEE!!",
    "THIS MOVE HAS NEVER BEEN USED BEFORE!! I CALL IT: DISCORD DESTROYER ABSOLUTE!! REEEEEEE!!",

    # See you in hell + named attack
    "SEE YOU IN HELL!! AND THE NAME OF THIS TECHNIQUE IS FORUM BAN FINALE!! REEEEEEEEE!!",
    "WE BOTH DIE TODAY!! FINAL MOVE: MUTUAL MODERATION DESTRUCTION!! REEEEEEEEEEE!!",
    "TO HELL WITH BOTH OF US!! SPECIAL TECHNIQUE: RESTRAINING ORDER RUSH!! REEEEEEEEE!!",
    "THIS IS MY HEROIC SACRIFICE ATTACK!! IT IS CALLED: MOTHER'S DISAPPOINTMENT BEAM!! REEEEEEE!!",
    "COME TO HELL WITH ME!! I CALL THIS MOVE THE SHIT-COMET TERMINUS!! REEEEEEEEEEE!!",

    # Tell my waifu / discord kitten + attack name
    "TELL MY WAIFU I DIED EXECUTING MY FINAL TECHNIQUE: THE LOG FINALIZER!! REEEEEEEEE!!",
    "TELL MY DISCORD KITTEN I UNLOCKED MY FINAL FORM!! THIS IS THE FINAL FORM!! REEEEEEE!!",
    "SOMEONE TELL MY WAIFU I WENT OUT WITH MY ULTIMATE MOVE: ASS-LANTERN IMPACT!! REEEEEEE!!",
    "TELL MY WAIFU BODY PILLOW THE NAME OF THIS ATTACK IS LOVE AND RAGE AND REEEEEE!!",
    "TELL MY DISCORD KITTEN I WASN'T LOGGING I WAS CHARGING MY FINAL ATTACK!! REEEEEEEEE!!",

    # Pure unhinged attack names
    "SPECIAL MOVE: MOIST WEDNESDAY IMPACT!! FEEL THE FULL FORCE OF A WEDNESDAY!! REEEEEEE!!",
    "FINAL FORM ACHIEVED!! ATTACK NAME: ABSOLUTE SCROTUM-ADJACENT OBLITERATION!! REEEEEEEEE!!",
    "THIS ATTACK IS CALLED THE MODERATOR ALPHA OMEGA ULTIMATE FINAL SPECIAL MOVE!! REEEEEEEEE!!",
]

# How long the wind-up flee phase lasts at minimum before kamikaze begins.
# The transition also waits for the speech bubble to finish, so short lines
# may fire sooner (minimum respected), long lines may take a little longer.
_WINDUP_MIN = 2.0    # seconds
_FLEE_SPEED  = 420   # pixels per second during wind-up


class AnnoyingKid(Enemy):
    """A very fast enemy that orbits the player at a safe distance and won't
    shut up about how ugly and bad at fighting the player is.

    Placement
    ---------
    Spawn like any other enemy::

        from data.enemy_stats import ENEMY_STATS
        from enemies.annoying_kid import AnnoyingKid

        kid = AnnoyingKid((cx, cy), ENEMY_STATS["annoying_kid"])
        map_obj.enemies.append(kid)
    """

    def __init__(self, position, stats):
        super().__init__(position, stats)

        # Obnoxious yellow speech, fast talker — 3 rows × 46 cols so even his
        # longest rants fit without dropping words
        self._speech = SpeechBubble(
            word_interval=0.224,
            duration=2.2,
            color=(255, 230, 30),
            rows=3,
            cols=46,
        )

        self.pattern = KeepDistancePattern(
            min_dist=100,
            max_dist=370,
            speed=350,
        )

        # Stagger the first quip so multiple kids don't all talk at once
        self._quip_timer = random.uniform(0.2, 1.5)

        # Rock-throwing state (normal phase only)
        self._rock_timer = 0.7
        self._rock_windup = 0.0
        self._holding_rock = False
        self._pending_rocks = []

        # Enrage / kamikaze state
        self._enraged = False
        self._winding_up = False    # flee + flash phase before the charge
        self._windup_timer = 0.0
        self._flash_cycle = 0.0     # sub-timer for the accelerating flash effect
        self._pending_explosion = False
        self._explosion_params = {}

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, dt, player, solid_regions, speed_factor=1.0):
        # Fall / landing — keep speech ticking but skip movement
        if self._update_fall(dt):
            if self.flash_timer > 0:
                self.flash_timer -= dt
            self._update_speech(dt)
            return

        # ── Enrage trigger ──────────────────────────────────────────────────
        if not self._enraged and self.health <= self.max_health * 0.6:
            self._enraged = True
            self._winding_up = True
            self._windup_timer = 0.0
            self._flash_cycle = 0.0
            self.say([random.choice(_ENRAGE_QUIPS)])

        # ── Wind-up phase: flee + accelerating flash ─────────────────────────
        # The kid runs away and shouts his final-attack line, then transitions
        # to a full kamikaze charge once the speech finishes and the minimum
        # wind-up time has elapsed.
        if self._winding_up:
            self._windup_timer += dt
            progress = min(self._windup_timer / _WINDUP_MIN, 1.0)

            # Flee directly away from the player (still facing them)
            to_player = player.pos - self.pos
            dist = to_player.length()
            if dist > 1.0:
                flee_dir = to_player / dist
                self.facing = flee_dir
                self.pos -= flee_dir * _FLEE_SPEED * dt

            # Flash period lerps from 0.35 s (calm) → 0.04 s (frantic)
            flash_period = 0.35 - 0.31 * progress
            self._flash_cycle += dt
            if self._flash_cycle >= flash_period:
                self._flash_cycle -= flash_period
                self.flash_timer = flash_period * 0.5

            # Transition: minimum time elapsed AND speech bubble mostly done
            if self._windup_timer >= _WINDUP_MIN and self._speech.progress >= 0.8:
                self._winding_up = False
                self.pattern = KamikazePattern(speed=500, explode_damage=6, explode_radius=120)
                self.flash_timer = 0.0

            self._update_knockback(dt)
            if self.flash_timer > 0:
                self.flash_timer -= dt
            self._update_speech(dt)
            return

        # ── Normal phase ─────────────────────────────────────────────────────
        if not self._enraged:
            self.pattern.player = player
            self.pattern.line_of_sight = _line_clear(
                self.pos.x, self.pos.y,
                player.pos.x, player.pos.y,
                solid_regions,
            )
            self.pattern.update(self, dt, speed_factor)

            self._quip_timer -= dt
            if self._quip_timer <= 0:
                if not self._speech.is_active:
                    self.say([random.choice(_QUIPS)])
                self._quip_timer = random.uniform(0.2, 1.2)

            # Rock throwing
            if self._holding_rock:
                self._rock_windup += dt
                if self._rock_windup >= 0.5:
                    # Fire the rock toward the player with wide angular spread
                    to_player = player.pos - self.pos
                    dist = to_player.length()
                    if dist > 1.0:
                        direction = to_player / dist
                    else:
                        direction = pygame.Vector2(0, 1)
                    angle_offset = math.radians(random.uniform(-40, 40))
                    direction = direction.rotate_rad(angle_offset)
                    self._pending_rocks.append(
                        Rock(self.pos, direction, dist, self.current_layer)
                    )
                    self._holding_rock = False
            else:
                self._rock_timer -= dt
                if self._rock_timer <= 0:
                    self._holding_rock = True
                    self._rock_windup = 0.0
                    self._rock_timer = 0.7

        # ── Kamikaze charge phase ─────────────────────────────────────────────
        else:
            self.pattern.player = player
            self.pattern.update(self, dt)

            if (player.pos - self.pos).length() <= 10 or self.pattern.should_explode:
                self._explosion_params = {
                    'radius': self.pattern.explode_radius,
                    'damage': self.pattern.explode_damage,
                    'shake': self.pattern.explode_shake,
                }
                self._pending_explosion = True
                self.health = 0
                return

        self._update_knockback(dt)

        if self.flash_timer > 0:
            self.flash_timer -= dt

        self._update_speech(dt)

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen, camera):
        super().draw(screen, camera)
        if self._holding_rock and not self.falling and not self.landing:
            screen_pos = pygame.Vector2(camera.apply(self.pos))
            rock_pos = (int(screen_pos.x - self.size),
                        int(screen_pos.y - self.size))
            pygame.draw.circle(screen, (140, 120, 90), rock_pos, 4)
