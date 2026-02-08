"""
Sound Manager — procedurally generated sound effects using pygame.

No external audio files required.  Uses numpy to generate waveforms and
wraps them in pygame.mixer.Sound objects.
"""
from __future__ import annotations
import math
import struct
import array
import pygame


class SoundManager:
    """Generates and plays procedural sound effects."""

    def __init__(self):
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self.sfx_volume: float = 0.5
        self.music_volume: float = 0.3
        self.master_volume: float = 0.7
        self.enabled: bool = True
        self._generate_all()

    # ══════════════════════════════════════════════════════
    #  Waveform helpers
    # ══════════════════════════════════════════════════════
    @staticmethod
    def _make_sound(samples: list[int], sample_rate: int = 44100) -> pygame.mixer.Sound:
        """Create a pygame Sound from a list of 16-bit signed samples (mono)."""
        # Pygame mixer expects stereo by default, so duplicate mono → stereo
        stereo = []
        for s in samples:
            s = max(-32767, min(32767, int(s)))
            stereo.append(s)
            stereo.append(s)
        buf = struct.pack(f"<{len(stereo)}h", *stereo)
        return pygame.mixer.Sound(buffer=buf)

    @staticmethod
    def _sine(freq: float, duration: float, volume: float = 0.5,
              sample_rate: int = 44100) -> list[int]:
        """Generate a sine wave."""
        n = int(sample_rate * duration)
        amp = int(32767 * volume)
        return [int(amp * math.sin(2 * math.pi * freq * i / sample_rate))
                for i in range(n)]

    @staticmethod
    def _square(freq: float, duration: float, volume: float = 0.3,
                sample_rate: int = 44100) -> list[int]:
        """Generate a square wave."""
        n = int(sample_rate * duration)
        amp = int(32767 * volume)
        period = sample_rate / freq
        return [amp if (i % int(period)) < int(period / 2) else -amp
                for i in range(n)]

    @staticmethod
    def _noise(duration: float, volume: float = 0.3,
               sample_rate: int = 44100) -> list[int]:
        """Generate white noise."""
        import random
        n = int(sample_rate * duration)
        amp = int(32767 * volume)
        return [random.randint(-amp, amp) for _ in range(n)]

    @staticmethod
    def _envelope(samples: list[int], attack: float = 0.01,
                  release: float = 0.05, sample_rate: int = 44100) -> list[int]:
        """Apply attack-release envelope to prevent clicks."""
        n = len(samples)
        attack_samples = int(attack * sample_rate)
        release_samples = int(release * sample_rate)
        out = list(samples)
        for i in range(min(attack_samples, n)):
            out[i] = int(out[i] * (i / attack_samples))
        for i in range(min(release_samples, n)):
            idx = n - 1 - i
            out[idx] = int(out[idx] * (i / release_samples))
        return out

    def _concat(self, *parts: list[int]) -> list[int]:
        """Concatenate multiple sample lists."""
        result = []
        for p in parts:
            result.extend(p)
        return result

    # ══════════════════════════════════════════════════════
    #  Sound definitions
    # ══════════════════════════════════════════════════════
    def _generate_all(self):
        """Generate all game sound effects."""
        sr = 44100

        # ── UI click (short blip) ────────────────────
        click = self._envelope(self._sine(800, 0.04, 0.3), 0.005, 0.02)
        self._sounds["click"] = self._make_sound(click, sr)

        # ── Button hover (soft tick) ─────────────────
        hover = self._envelope(self._sine(600, 0.02, 0.15), 0.003, 0.01)
        self._sounds["hover"] = self._make_sound(hover, sr)

        # ── Build start (descending tone) ────────────
        s1 = self._sine(500, 0.08, 0.3)
        s2 = self._sine(400, 0.08, 0.3)
        s3 = self._sine(350, 0.12, 0.3)
        build = self._envelope(self._concat(s1, s2, s3), 0.01, 0.04)
        self._sounds["build_start"] = self._make_sound(build, sr)

        # ── Build complete (ascending fanfare) ───────
        f1 = self._sine(523, 0.1, 0.4)   # C5
        f2 = self._sine(659, 0.1, 0.4)   # E5
        f3 = self._sine(784, 0.15, 0.4)  # G5
        f4 = self._sine(1047, 0.25, 0.4) # C6
        fanfare = self._envelope(self._concat(f1, f2, f3, f4), 0.01, 0.08)
        self._sounds["build_complete"] = self._make_sound(fanfare, sr)

        # ── Troop trained (march-like) ───────────────
        t1 = self._sine(440, 0.08, 0.3)
        t2 = self._sine(554, 0.08, 0.3)
        t3 = self._sine(659, 0.12, 0.3)
        march = self._envelope(self._concat(t1, t2, t3), 0.01, 0.04)
        self._sounds["troop_trained"] = self._make_sound(march, sr)

        # ── Research complete ────────────────────────
        r1 = self._sine(392, 0.12, 0.35)  # G4
        r2 = self._sine(523, 0.12, 0.35)  # C5
        r3 = self._sine(659, 0.12, 0.35)  # E5
        r4 = self._sine(784, 0.2, 0.35)   # G5
        research = self._envelope(self._concat(r1, r2, r3, r4), 0.01, 0.06)
        self._sounds["research_complete"] = self._make_sound(research, sr)

        # ── Quest complete (reward jingle) ───────────
        q1 = self._sine(587, 0.07, 0.35)  # D5
        q2 = self._sine(740, 0.07, 0.35)  # F#5
        q3 = self._sine(880, 0.07, 0.35)  # A5
        q4 = self._sine(1175, 0.2, 0.35)  # D6
        quest = self._envelope(self._concat(q1, q2, q3, q4), 0.01, 0.06)
        self._sounds["quest_complete"] = self._make_sound(quest, sr)

        # ── Battle hit (noise burst) ─────────────────
        hit = self._envelope(self._noise(0.06, 0.4), 0.003, 0.03)
        self._sounds["battle_hit"] = self._make_sound(hit, sr)

        # ── Victory (triumphant) ─────────────────────
        v1 = self._sine(523, 0.12, 0.4)   # C5
        v2 = self._sine(659, 0.12, 0.4)   # E5
        v3 = self._sine(784, 0.15, 0.4)   # G5
        v4 = self._sine(1047, 0.3, 0.5)   # C6
        # Layer with harmonics
        v4h = self._sine(1568, 0.3, 0.2)  # G6 harmony
        for i in range(len(v4)):
            v4[i] = int((v4[i] + v4h[i]) * 0.6)
        victory = self._envelope(self._concat(v1, v2, v3, v4), 0.01, 0.1)
        self._sounds["victory"] = self._make_sound(victory, sr)

        # ── Defeat (sad descending) ──────────────────
        d1 = self._sine(440, 0.2, 0.35)   # A4
        d2 = self._sine(392, 0.2, 0.35)   # G4
        d3 = self._sine(330, 0.3, 0.35)   # E4
        d4 = self._sine(262, 0.4, 0.3)    # C4
        defeat = self._envelope(self._concat(d1, d2, d3, d4), 0.01, 0.15)
        self._sounds["defeat"] = self._make_sound(defeat, sr)

        # ── Error / deny ─────────────────────────────
        e1 = self._square(200, 0.1, 0.2)
        e2 = self._square(150, 0.15, 0.2)
        error = self._envelope(self._concat(e1, e2), 0.005, 0.05)
        self._sounds["error"] = self._make_sound(error, sr)

        # ── Save game (confirmation chime) ───────────
        sv1 = self._sine(880, 0.08, 0.3)
        sv2 = self._sine(1100, 0.12, 0.3)
        save = self._envelope(self._concat(sv1, sv2), 0.005, 0.04)
        self._sounds["save"] = self._make_sound(save, sr)

        # ── Level up (hero level up) ─────────────────
        lu1 = self._sine(523, 0.06, 0.35)
        lu2 = self._sine(659, 0.06, 0.35)
        lu3 = self._sine(784, 0.06, 0.35)
        lu4 = self._sine(1047, 0.06, 0.35)
        lu5 = self._sine(1318, 0.15, 0.4)
        lvlup = self._envelope(self._concat(lu1, lu2, lu3, lu4, lu5), 0.005, 0.06)
        self._sounds["level_up"] = self._make_sound(lvlup, sr)

    # ══════════════════════════════════════════════════════
    #  Playback
    # ══════════════════════════════════════════════════════
    def play(self, name: str):
        """Play a named sound effect."""
        if not self.enabled:
            return
        snd = self._sounds.get(name)
        if snd:
            vol = self.sfx_volume * self.master_volume
            snd.set_volume(max(0.0, min(1.0, vol)))
            snd.play()

    def set_sfx_volume(self, vol: float):
        self.sfx_volume = max(0.0, min(1.0, vol))

    def set_master_volume(self, vol: float):
        self.master_volume = max(0.0, min(1.0, vol))

    def toggle(self) -> bool:
        """Toggle sound on/off. Returns new state."""
        self.enabled = not self.enabled
        return self.enabled

    def to_dict(self) -> dict:
        return {
            "sfx_volume": self.sfx_volume,
            "music_volume": self.music_volume,
            "master_volume": self.master_volume,
            "enabled": self.enabled,
        }

    def from_dict(self, data: dict):
        self.sfx_volume = data.get("sfx_volume", 0.5)
        self.music_volume = data.get("music_volume", 0.3)
        self.master_volume = data.get("master_volume", 0.7)
        self.enabled = data.get("enabled", True)


# ── Singleton ────────────────────────────────────────────
_instance: SoundManager | None = None


def get_sound_manager() -> SoundManager:
    global _instance
    if _instance is None:
        _instance = SoundManager()
    return _instance
