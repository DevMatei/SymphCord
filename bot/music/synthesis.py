import io
import logging
import math
import os
from typing import Dict, Iterable, Tuple

from pydub import AudioSegment
from pydub.generators import Sawtooth, Sine, Square, Triangle

from .types import InstrumentWave, NoteEvent

try:  # optional real-instrument rendering
    import numpy as np
    import pretty_midi
    try:
        import fluidsynth  # noqa: F401  # ensure pyfluidsynth is present
    except ImportError:  # pragma: no cover - optional dependency
        fluidsynth = None  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    np = None  # type: ignore
    pretty_midi = None  # type: ignore
    fluidsynth = None  # type: ignore


_LOG = logging.getLogger("symphcord.synthesis")
_SOUNDFONT_PATH = os.getenv("SOUNDFONT_PATH")

if _SOUNDFONT_PATH and pretty_midi and np is not None and fluidsynth is None:
    _LOG.warning(
        "SOUNDFONT_PATH provided but pyfluidsynth is missing; install it with 'pip install pyfluidsynth'."
    )

GENERATOR_MAP = {
    InstrumentWave.SINE: Sine,
    InstrumentWave.SQUARE: Square,
    InstrumentWave.SAWTOOTH: Sawtooth,
    InstrumentWave.TRIANGLE: Triangle,
    InstrumentWave.WARM: Sine,
    InstrumentWave.BELL: Sine,
    InstrumentWave.PULSE: Triangle,
    InstrumentWave.GLOW: Triangle,
    InstrumentWave.HARP: Sine,
    InstrumentWave.CELESTA: Sine,
    InstrumentWave.CHOIR: Sine,
}

MIDI_PROGRAMS: Dict[InstrumentWave, int] = {
    InstrumentWave.SINE: 0,  # Acoustic Grand Piano
    InstrumentWave.WARM: 88,  # Pad 1 (New Age)
    InstrumentWave.BELL: 11,  # Vibraphone
    InstrumentWave.PULSE: 13,  # Marimba for soft pulses
    InstrumentWave.GLOW: 91,  # Pad 4 (choir)
    InstrumentWave.HARP: 46,  # Orchestral Harp
    InstrumentWave.CELESTA: 8,  # Celesta
    InstrumentWave.CHOIR: 52,  # Choir Aahs
    InstrumentWave.SQUARE: 0,
    InstrumentWave.SAWTOOTH: 0,
    InstrumentWave.TRIANGLE: 0,
}


def _soft_filter(segment: AudioSegment) -> AudioSegment:
    # trim sharp highs and low rumbles to keep the tone gentle
    filtered = segment.low_pass_filter(6400).high_pass_filter(120)
    return filtered


def _apply_reverb(segment: AudioSegment) -> AudioSegment:
    reflections = [110, 260, 430]
    mix = AudioSegment.silent(
        duration=len(segment) + reflections[-1],
        frame_rate=segment.frame_rate,
    ).overlay(segment, position=0)
    for idx, delay in enumerate(reflections):
        decay = segment.apply_gain(-12 - idx * 5)
        mix = mix.overlay(decay, position=delay)
    return mix


def _build_segment(note: NoteEvent, duration_ms: int, sample_rate: int) -> AudioSegment:
    amplitude = max(0.1, min(note.amplitude, 0.85))
    generator_cls = GENERATOR_MAP.get(note.instrument, Sine)
    layers: list[AudioSegment] = [
        generator_cls(
            note.frequency,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms)
    ]
    attack = max(15, int(duration_ms * 0.18))
    release = max(60, int(duration_ms * 0.35))

    if note.instrument == InstrumentWave.WARM:
        lower = Sine(
            max(note.frequency / 2, 55.0),
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-12.0)
        shimmer = Triangle(
            note.frequency * 2,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-15.0)
        layers.extend([lower, shimmer])
    elif note.instrument == InstrumentWave.BELL:
        overtone = Sine(
            note.frequency * 2.5,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-8.0)
        chime = Triangle(
            note.frequency * 3.5,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-14.0)
        layers.extend([overtone, chime])
    elif note.instrument == InstrumentWave.PULSE:
        accent = Triangle(
            note.frequency * 2,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-10.0)
        sub = Sine(
            max(note.frequency / 2, 40.0),
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-14.0)
        layers.extend([accent, sub])
    elif note.instrument == InstrumentWave.GLOW:
        breath = Sine(
            max(note.frequency / 2.5, 30.0),
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-18.0)
        shimmer = Triangle(
            note.frequency * 1.6,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-14.0)
        layers.extend([breath, shimmer])
    elif note.instrument == InstrumentWave.HARP:
        accent = Triangle(
            note.frequency,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-8.0)
        ping = Sine(
            note.frequency * 2,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-12.0)
        layers.extend([accent, ping])
        attack = max(5, int(duration_ms * 0.05))
        release = max(80, int(duration_ms * 0.4))
    elif note.instrument == InstrumentWave.CELESTA:
        chime = Sine(
            note.frequency * 2.8,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-6.0)
        tinkle = Triangle(
            note.frequency * 4.2,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-15.0)
        layers.extend([chime, tinkle])
        attack = max(6, int(duration_ms * 0.08))
        release = max(70, int(duration_ms * 0.3))
    elif note.instrument == InstrumentWave.CHOIR:
        airy = Sine(
            note.frequency * 0.5,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-12.0)
        vowel = Square(
            note.frequency,
            sample_rate=sample_rate,
            bit_depth=16,
        ).to_audio_segment(duration=duration_ms).apply_gain(-18.0)
        layers.extend([airy, vowel])
        attack = max(25, int(duration_ms * 0.25))
        release = max(120, int(duration_ms * 0.45))

    segment = layers[0]
    for layer in layers[1:]:
        segment = segment.overlay(layer)

    gain_db = 20 * math.log10(amplitude)
    segment = segment.apply_gain(gain_db).fade_in(attack).fade_out(release)
    segment = _soft_filter(segment)
    return _add_air(segment)


def _add_air(segment: AudioSegment) -> AudioSegment:
    reverb = _apply_reverb(segment)
    shimmer = reverb.high_pass_filter(1800).apply_gain(-12)
    delay = segment.overlay(segment.apply_gain(-9), position=90)
    blended = segment.overlay(reverb.apply_gain(-6))
    blended = blended.overlay(shimmer)
    blended = blended.overlay(delay)
    return blended


def _frequency_to_midi(freq: float) -> int:
    if freq <= 0:
        return 60
    midi = 69 + 12 * math.log2(freq / 440.0)
    return int(max(21, min(108, round(midi))))


def _render_with_soundfont(
    events: Iterable[NoteEvent],
    total_duration: float,
    sample_rate: int,
) -> Tuple[io.BytesIO, float]:
    if pretty_midi is None or np is None or not _SOUNDFONT_PATH or fluidsynth is None:
        raise RuntimeError("SoundFont rendering is not available.")

    pm = pretty_midi.PrettyMIDI(resolution=960)
    instrument_tracks: Dict[int, pretty_midi.Instrument] = {}

    for event in events:
        program = MIDI_PROGRAMS.get(event.instrument, 0)
        track = instrument_tracks.get(program)
        if track is None:
            track = pretty_midi.Instrument(program=program)
            instrument_tracks[program] = track
            pm.instruments.append(track)

        velocity = int(max(32, min(118, event.amplitude * 127)))
        note_number = _frequency_to_midi(event.frequency)
        note = pretty_midi.Note(
            velocity=velocity,
            pitch=note_number,
            start=max(event.start, 0.0),
            end=max(event.start + event.duration, event.start + 0.15),
        )
        track.notes.append(note)
# hi 
    if not pm.instruments:
        raise RuntimeError("No instruments to render via SoundFont.")

    try:
        audio = pm.fluidsynth(fs=sample_rate, sf2_path=_SOUNDFONT_PATH)
    except TypeError:  # pretty_midi versions <0.2.10
        audio = pm.fluidsynth(sample_rate, _SOUNDFONT_PATH)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    audio = np.clip(audio, -1.0, 1.0)
    samples = (audio * 32767).astype(np.int16)
    segment = AudioSegment(
        samples.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1,
    )
    segment = _soft_filter(segment)
    segment = _add_air(segment)

    buffer = io.BytesIO()
    segment.export(buffer, format="wav")
    buffer.seek(0)
    return buffer, total_duration


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

    if _SOUNDFONT_PATH and pretty_midi and np is not None:
        try:
            return _render_with_soundfont(scaled_events, total_duration, sample_rate)
        except Exception as exc:  # pragma: no cover - optional path
            _LOG.warning("SoundFont rendering failed (%s); falling back to synth", exc)

    tail = 1.0
    track_length = int(math.ceil((total_duration + tail) * 1000))
    output = AudioSegment.silent(duration=track_length, frame_rate=sample_rate)

    for note in scaled_events:
        duration_ms = max(int(note.duration * 1000), 80)
        segment = _build_segment(note, duration_ms, sample_rate)
        start_ms = int(note.start * 1000)
        output = output.overlay(segment, position=start_ms)

    peak_level = output.max_dBFS
    if math.isfinite(peak_level):
        if peak_level < -1.5:
            output = output.apply_gain(-1.5 - peak_level)
    else:
        output = output.apply_gain(6.0)

    buffer = io.BytesIO()
    output.export(buffer, format="wav")
    buffer.seek(0)
    return buffer, total_duration
