import math
import string
from datetime import datetime
from typing import Iterable, List, Sequence

import discord

from .types import InstrumentWave, NoteEvent

MAJOR_SCALE_STEPS: Sequence[int] = (0, 2, 4, 5, 7, 9, 11)
ROOT_MIDI = 60  # middle C
SCALE_MIDI_NOTES: List[int] = [
    ROOT_MIDI + octave * 12 + step
    for octave in range(3)
    for step in MAJOR_SCALE_STEPS
]


def midi_to_frequency(midi_note: int) -> float:
    return 440.0 * math.pow(2, (midi_note - 69) / 12)


def _caps_and_punct_weight(text: str) -> float:
    if not text:
        return 0.0
    caps = sum(1 for c in text if c.isupper())
    punct = sum(1 for c in text if c in string.punctuation)
    weighted = (caps * 1.2 + punct) / max(len(text), 1)
    return min(weighted, 1.0)


def _select_instrument(author: discord.abc.User) -> InstrumentWave:
    instrument_options = list(InstrumentWave)
    author_id = getattr(author, "id", 0) or 0
    return instrument_options[author_id % len(instrument_options)]


def _quantize(delta_seconds: float, beat: float) -> float:
    if delta_seconds <= 0:
        return 0.0
    beats = round(delta_seconds / beat)
    return beats * beat


def _note_duration(message: discord.Message, beat: float) -> float:
    length = len(message.content.strip())
    if length <= 0:
        return beat
    max_extra = beat * 1.5
    return beat * 0.8 + min(length / 120.0, 1.0) * max_extra


def _message_to_note(
    message: discord.Message,
    first_timestamp: datetime,
    beat: float,
) -> NoteEvent:
    content = message.content.strip()
    length = max(len(content), 1)
    midi_idx = length % len(SCALE_MIDI_NOTES)
    midi_note = SCALE_MIDI_NOTES[midi_idx]
    frequency = midi_to_frequency(midi_note)

    intensity = _caps_and_punct_weight(content)
    amplitude = 0.45 + intensity * 0.45

    instrument = _select_instrument(message.author)

    delta = (message.created_at - first_timestamp).total_seconds()
    start = _quantize(max(delta, 0.0), beat)
    duration = _note_duration(message, beat)

    return NoteEvent(
        start=start,
        duration=duration,
        frequency=frequency,
        amplitude=min(amplitude, 0.9),
        instrument=instrument,
    )


def notes_from_messages(messages: Iterable[discord.Message], beat: float = 0.5) -> List[NoteEvent]:
    filtered: List[discord.Message] = [
        msg for msg in messages if msg.content and not msg.author.bot
    ]
    if not filtered:
        return []

    filtered.sort(key=lambda m: m.created_at)
    first_timestamp = filtered[0].created_at

    events = [
        _message_to_note(message, first_timestamp, beat)
        for message in filtered
    ]
    return events
