import io
import math
from typing import Iterable, Tuple

from pydub import AudioSegment
from pydub.generators import Sawtooth, Sine, Square, Triangle

from .types import InstrumentWave, NoteEvent

GENERATOR_MAP = {
    InstrumentWave.SINE: Sine,
    InstrumentWave.SQUARE: Square,
    InstrumentWave.SAWTOOTH: Sawtooth,
    InstrumentWave.TRIANGLE: Triangle,
}


def _scale_events(
    events: Iterable[NoteEvent],
    min_duration: float,
    max_duration: float,
) -> Tuple[list[NoteEvent], float]:
    event_list = list(events)
    if not event_list:
        return [], 0.0

    base_length = max(note.start + note.duration for note in event_list)
    if base_length <= 0:
        base_length = min_duration

    target = max(min_duration, min(base_length, max_duration))
    if base_length < min_duration or base_length > max_duration:
        target = max(min_duration, min(max_duration, base_length))

    if base_length == 0:
        scale = 1.0
    else:
        scale = target / base_length

    scaled_events = [
        NoteEvent(
            start=note.start * scale,
            duration=note.duration * scale,
            frequency=note.frequency,
            amplitude=note.amplitude,
            instrument=note.instrument,
        )
        for note in event_list
    ]

    final_length = max(note.start + note.duration for note in scaled_events)
    return scaled_events, final_length


def render_notes_to_wav(
    events: Iterable[NoteEvent],
    min_duration: float = 15.0,
    max_duration: float = 30.0,
    sample_rate: int = 44100,
) -> tuple[io.BytesIO, float]:
    scaled_events, total_duration = _scale_events(events, min_duration, max_duration)
    if not scaled_events:
        raise ValueError("No events to render.")

    tail = 0.5
    track_length = int(math.ceil((total_duration + tail) * 1000))
    output = AudioSegment.silent(duration=track_length, frame_rate=sample_rate)

    for note in scaled_events:
        generator_cls = GENERATOR_MAP.get(note.instrument, Sine)
        generator = generator_cls(
            note.frequency,
            sample_rate=sample_rate,
            bit_depth=16,
        )
        duration_ms = max(int(note.duration * 1000), 50)
        segment = generator.to_audio_segment(duration=duration_ms)
        amplitude = max(0.05, min(note.amplitude, 1.0))
        gain_db = 20 * math.log10(amplitude)
        segment = segment.apply_gain(gain_db)
        segment = segment.fade_in(10).fade_out(20)
        start_ms = int(note.start * 1000)
        output = output.overlay(segment, position=start_ms)

    output = output.apply_gain(-3.0)

    buffer = io.BytesIO()
    output.export(buffer, format="wav")
    buffer.seek(0)
    return buffer, total_duration
