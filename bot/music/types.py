from dataclasses import dataclass
from enum import Enum


class InstrumentWave(Enum):
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    TRIANGLE = "triangle"
    WARM = "warm"
    BELL = "bell"
    PULSE = "pulse"
    GLOW = "glow"
    HARP = "harp"
    CELESTA = "celesta"
    CHOIR = "choir"


@dataclass
class NoteEvent:
    start: float  # seconds
    duration: float  # seconds
    frequency: float  # Hz
    amplitude: float  # 0..1
    instrument: InstrumentWave
