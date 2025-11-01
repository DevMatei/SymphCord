import math
import string
from datetime import datetime
from typing import Iterable, List, Optional, Sequence

import discord

from .types import InstrumentWave, NoteEvent

MAJOR_SCALE_STEPS: Sequence[int] = (0, 2, 4, 7, 9, 11)  # Lydian-ish for lift
ROOT_MIDI = 62  # start on D for brighter tonic
SCALE_MIDI_NOTES: List[int] = [
    ROOT_MIDI + octave * 12 + step
    for octave in range(3)
    for step in MAJOR_SCALE_STEPS
]


def midi_to_frequency(midi_note: int) -> float:
    return 440.0 * math.pow(2, (midi_note - 69) / 12)


def _nearest_scale_frequency(target: float) -> float:
    return min(
        (midi_to_frequency(note) for note in SCALE_MIDI_NOTES),
        key=lambda freq: abs(freq - target),
    )


def _caps_and_punct_weight(text: str) -> float:
    if not text:
        return 0.0
    caps = sum(1 for c in text if c.isupper())
    punct = sum(1 for c in text if c in string.punctuation)
    weighted = (caps * 1.2 + punct) / max(len(text), 1)
    return min(weighted, 1.0)


def _select_instrument(author: discord.abc.User) -> InstrumentWave:
    palette = [
        InstrumentWave.WARM,
        InstrumentWave.SINE,
        InstrumentWave.BELL,
        InstrumentWave.GLOW,
        InstrumentWave.HARP,
        InstrumentWave.CELESTA,
    ]
    author_id = getattr(author, "id", 0) or 0
    return palette[author_id % len(palette)]


def _content_pitch_index(content: str) -> int:
    filtered = "".join(c for c in content if c.isalnum())
    if not filtered:
        return len(SCALE_MIDI_NOTES) // 2
    ascii_sum = sum(ord(c) for c in filtered)
    vowel_bonus = sum(1 for c in filtered.lower() if c in "aeiou") * 3
    return (ascii_sum + vowel_bonus) % len(SCALE_MIDI_NOTES)


def _smooth_pitch_index(base_idx: int, previous_idx: Optional[int]) -> int:
    if previous_idx is None:
        return base_idx

    total_notes = len(SCALE_MIDI_NOTES)
    candidates = [base_idx, base_idx + total_notes, base_idx - total_notes]
    closest = min(candidates, key=lambda val: abs(val - previous_idx))
    closest = max(0, min(total_notes - 1, closest))

    if abs(closest - previous_idx) > 2:
        if closest > previous_idx:
            closest = min(previous_idx + 2, total_notes - 1)
        else:
            closest = max(previous_idx - 2, 0)
    return closest


def _quantize(delta_seconds: float, beat: float) -> float:
    if delta_seconds <= 0:
        return 0.0
    beats = round(delta_seconds / beat)
    return beats * beat


def _note_duration(message: discord.Message, beat: float) -> float:
    length = len(message.content.strip())
    if length <= 0:
        return beat
    max_extra = beat * 3.0
    stretch_factor = min(length / 95.0, 1.0)
    return beat * 1.1 + stretch_factor * max_extra


def _message_to_note(
    message: discord.Message,
    first_timestamp: datetime,
    beat: float,
    previous_idx: Optional[int],
    previous_start: Optional[float],
) -> tuple[NoteEvent, int, float]:
    content = message.content.strip()
    base_idx = _content_pitch_index(content)
    midi_idx = _smooth_pitch_index(base_idx, previous_idx)
    midi_note = SCALE_MIDI_NOTES[midi_idx]
    frequency = midi_to_frequency(midi_note)

    intensity = _caps_and_punct_weight(content)
    amplitude = 0.28 + intensity * 0.28

    instrument = _select_instrument(message.author)

    delta = (message.created_at - first_timestamp).total_seconds()
    raw_start = _quantize(max(delta, 0.0), beat)

    if previous_start is None:
        start = raw_start
    else:
        previous_beats = previous_start / beat
        raw_beats = raw_start / beat
        min_gap_beats = 1.0
        max_gap_beats = 2.5
        start_beats = max(raw_beats, previous_beats + min_gap_beats)
        if start_beats - previous_beats > max_gap_beats:
            start_beats = previous_beats + max_gap_beats
        start = start_beats * beat

    duration = _note_duration(message, beat)
    note = NoteEvent(
        start=start,
        duration=duration,
        frequency=frequency,
        amplitude=min(amplitude, 0.9),
        instrument=instrument,
    )

    return note, midi_idx, start


def _harmonic_from(note: NoteEvent, semitone_shift: int, amplitude_scale: float, instrument: InstrumentWave) -> NoteEvent:
    frequency = note.frequency * math.pow(2, semitone_shift / 12.0)
    return NoteEvent(
        start=note.start,
        duration=note.duration * 1.1,
        frequency=frequency,
        amplitude=min(note.amplitude * amplitude_scale, 0.55),
        instrument=instrument,
    )


def _fill_gaps(notes: List[NoteEvent], beat: float) -> List[NoteEvent]:
    if not notes:
        return []
    filled: List[NoteEvent] = [notes[0]]
    for prev, curr in zip(notes, notes[1:]):
        gap = curr.start - prev.start
        if gap > beat * 1.4:
            earliest = prev.start + beat * 0.35
            latest = curr.start - beat * 0.35
            insert_start = min(max(prev.start + gap * 0.55, earliest), latest)
            duration = min(curr.start - insert_start, beat * 0.9)
            duration = max(duration, beat * 0.45)
            blended = (prev.frequency * 0.45) + (curr.frequency * 0.55)
            frequency = _nearest_scale_frequency(blended)
            filler = NoteEvent(
                start=insert_start,
                duration=duration,
                frequency=frequency,
                amplitude=min(max(prev.amplitude, curr.amplitude) * 0.45, 0.45),
                instrument=InstrumentWave.GLOW,
            )
            filled.append(filler)
        filled.append(curr)
    return sorted(filled, key=lambda n: n.start)


def _background_pad(notes: List[NoteEvent]) -> List[NoteEvent]:
    if not notes:
        return []
    track_end = max(n.start + n.duration for n in notes)
    root_note = min(notes, key=lambda n: n.frequency)
    pad_frequency = root_note.frequency
    pad_duration = track_end + 1.5
    pad = NoteEvent(
        start=0.0,
        duration=pad_duration,
        frequency=pad_frequency,
        amplitude=0.16,
        instrument=InstrumentWave.WARM,
    )
    shimmer = NoteEvent(
        start=0.0,
        duration=pad_duration,
        frequency=pad_frequency * math.pow(2, 12 / 12.0),
        amplitude=pad.amplitude * 0.45,
        instrument=InstrumentWave.CELESTA,
    )
    choir = NoteEvent(
        start=0.0,
        duration=pad_duration,
        frequency=pad_frequency * math.pow(2, -12 / 12.0),
        amplitude=pad.amplitude * 0.4,
        instrument=InstrumentWave.CHOIR,
    )
    return [pad, shimmer, choir]


def notes_from_messages(messages: Iterable[discord.Message], beat: float = 0.55) -> List[NoteEvent]:
    filtered: List[discord.Message] = []
    for msg in messages:
        if not msg.content:
            continue
        if getattr(msg.author, "bot", False):
            continue
        if msg.webhook_id:
            continue
        is_system = False
        try:
            is_system = msg.is_system()
        except TypeError:
            is_system = False
        if is_system:
            continue
        filtered.append(msg)
    if not filtered:
        return []

    filtered.sort(key=lambda m: m.created_at)
    first_timestamp = filtered[0].created_at

    events: List[NoteEvent] = []
    previous_idx: Optional[int] = None
    previous_start: Optional[float] = None
    for message in filtered:
        note, previous_idx, previous_start = _message_to_note(
            message,
            first_timestamp,
            beat,
            previous_idx,
            previous_start,
        )
        events.append(note)

    layered: List[NoteEvent] = []
    for idx, note in enumerate(events):
        layered.append(note)
        layered.append(_harmonic_from(note, 4, 0.45, InstrumentWave.CELESTA))
        if idx % 2 == 0:
            layered.append(_harmonic_from(note, 7, 0.34, InstrumentWave.SINE))
        if idx % 3 == 0:
            layered.append(_harmonic_from(note, 12, 0.24, InstrumentWave.GLOW))

    layered = _fill_gaps(layered, beat)
    layered.extend(_background_pad(layered))
    return layered
