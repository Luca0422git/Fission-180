#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Writes Neon Lights' UI sounds (docs/fission180/neon-lights-design.md 6.9) as small WAV files.

Every sound is synthesized here from sine, square and noise waves with the standard library
(`wave`, `math`, `random` with a fixed seed), so they are Fission 180's own: no samples, no
licences. The same script always writes the same files (unit test test_make_sounds.py).

    python3 tools/fission180/make_sounds.py [out_dir]   (default: the module's fission180/sounds)
"""

import math
import os
import random
import struct
import sys
import wave

RATE = 22050  # samples per second: plenty for short blips, and keeps every file small
NAMES = ("click", "menu", "done", "error", "boot")
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(
    HERE, "..", "..", "src", "Mod", "Fission180", "fission180", "sounds"
)


def _env(t, length, attack=0.004, release=None):
    """A quick fade in and an exponential fade out, so no blip clicks at its ends."""
    if t < attack:
        return t / attack
    release = release or length
    rest = max(0.0, length - t)
    tail = min(1.0, rest / 0.006)  # the last 6 ms always fade to silence
    return math.exp(-3.0 * (t - attack) / release) * tail


def _square(phase, softness=0.25):
    """A square wave with rounded edges (a pure square is harsh at UI volume)."""
    return math.tanh(math.sin(phase) / softness) * 0.8


def _sweep(t, f0, f1, length):
    """The phase of a tone gliding from f0 to f1 Hz over `length` seconds."""
    k = (f1 - f0) / length
    return 2.0 * math.pi * (f0 * t + 0.5 * k * t * t)


def click(n):
    """A short bright tick with a little noise: a button pressed."""
    rnd = random.Random(180)
    length = n / RATE
    out = []
    for i in range(n):
        t = i / RATE
        tone = math.sin(_sweep(t, 2400, 1600, length)) * 0.6
        noise = (rnd.random() * 2 - 1) * 0.25 * math.exp(-t / 0.004)
        out.append((tone + noise) * _env(t, length, 0.001, 0.012))
    return out


def menu(n):
    """Two quick rising notes: a menu opening."""
    length = n / RATE
    half = length / 2
    out = []
    for i in range(n):
        t = i / RATE
        f = 880.0 if t < half else 1320.0
        local = t if t < half else t - half
        v = _square(2 * math.pi * f * t, 0.5) * 0.5 + math.sin(4 * math.pi * f * t) * 0.15
        out.append(v * _env(local, half, 0.002, 0.03))
    return out


def done(n):
    """A three-note rising arpeggio with a soft tail: a command finished."""
    notes = (659.25, 987.77, 1318.51)  # E5, B5, E6
    step = 0.055
    length = n / RATE
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        for k, f in enumerate(notes):
            start = k * step
            if t >= start:
                local = t - start
                v += math.sin(2 * math.pi * f * local) * _env(local, length - start, 0.003, 0.08)
                v += 0.25 * math.sin(4 * math.pi * f * local) * _env(local, length - start, 0.003, 0.04)
        out.append(v * 0.38)
    return out


def error(n):
    """Two low buzzes, falling: something went wrong."""
    length = n / RATE
    gap = length / 2
    out = []
    for i in range(n):
        t = i / RATE
        local = t if t < gap else t - gap
        f = 220.0 if t < gap else 164.81
        v = _square(2 * math.pi * f * t, 0.35) * 0.55
        v += math.sin(2 * math.pi * f * 1.5 * t) * 0.2  # a fifth above, for the edge
        out.append(v * _env(local, gap, 0.004, 0.09))
    return out


def boot(n):
    """A rising sweep with a shimmer and a chord at the end: the boot screen."""
    rnd = random.Random(1801)  # a fixed seed: the noise is the same every time
    length = n / RATE
    rise = length * 0.55
    out = []
    for i in range(n):
        t = i / RATE
        if t < rise:
            phase = _sweep(t, 110, 880, rise)
            v = _square(phase, 0.6) * 0.35 * (t / rise)
            v += (rnd.random() * 2 - 1) * 0.06 * (t / rise)
        else:
            local = t - rise
            v = 0.0
            for f, w in ((440.0, 0.32), (659.25, 0.24), (880.0, 0.2), (1318.51, 0.08)):
                v += math.sin(2 * math.pi * f * local + f) * w
            shimmer = 0.5 + 0.5 * math.sin(2 * math.pi * 7.0 * local)
            v *= _env(local, length - rise, 0.006, 0.18) * (0.8 + 0.2 * shimmer)
        out.append(v * _env(t, length, 0.01, 10.0))
    return out


# name -> (synth, length in seconds)
SOUNDS = {
    "click": (click, 0.035),
    "menu": (menu, 0.09),
    "done": (done, 0.32),
    "error": (error, 0.30),
    "boot": (boot, 1.1),
}


def samples(name):
    """The sound as 16-bit integers (deterministic)."""
    synth, seconds = SOUNDS[name]
    n = int(RATE * seconds)
    out = []
    for v in synth(n):
        v = max(-1.0, min(1.0, v))
        out.append(int(round(v * 0.7 * 32767)))  # 0.7: headroom, and UI sounds stay polite
    return out


def write(path, values, rate=RATE):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<%dh" % len(values), *values))


def make(out_dir=DEFAULT_OUT):
    """Write every sound into out_dir; returns the paths."""
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name in NAMES:
        path = os.path.join(out_dir, name + ".wav")
        write(path, samples(name))
        paths.append(path)
    return paths


if __name__ == "__main__":
    for p in make(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT):
        print("[Fission 180] %s (%d bytes)" % (p, os.path.getsize(p)))
