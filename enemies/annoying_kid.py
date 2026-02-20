import random

from core.enemy_base import Enemy, _line_clear
from core.speech_bubble import SpeechBubble
from patterns.enemy_patterns import KeepDistancePattern

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
            word_interval=0.28,
            duration=2.2,
            color=(255, 230, 30),
            rows=3,
            cols=46,
        )

        self.pattern = KeepDistancePattern(
            min_dist=200,
            max_dist=370,
            speed=350,
        )

        # Stagger the first quip so multiple kids don't all talk at once
        self._quip_timer = random.uniform(0.2, 1.5)

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, dt, player, solid_regions):
        # Fall / landing — keep speech ticking but skip movement
        if self._update_fall(dt):
            if self.flash_timer > 0:
                self.flash_timer -= dt
            self._update_speech(dt)
            return

        # Movement — always track the player at a distance.
        # Pass line-of-sight so the pattern can switch between orbiting
        # (clear path) and direct pursuit (wall in the way → find the doorway).
        self.pattern.player = player
        self.pattern.line_of_sight = _line_clear(
            self.pos.x, self.pos.y,
            player.pos.x, player.pos.y,
            solid_regions,
        )
        self.pattern.update(self, dt)

        # Quips — fire whenever the bubble goes idle
        self._quip_timer -= dt
        if self._quip_timer <= 0:
            if not self._speech.is_active:
                self.say([random.choice(_QUIPS)])
            self._quip_timer = random.uniform(0.2, 1.2)

        self._update_knockback(dt)

        if self.flash_timer > 0:
            self.flash_timer -= dt

        self._update_speech(dt)
