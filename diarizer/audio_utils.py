import collections
import contextlib
import wave
import numpy as np
import webrtcvad
import logging

logger = logging.getLogger(__name__)

def read_wave(path):
    """
    Read a WAV file and return the PCM data and frame rate.
    
    Args:
        path: Path to WAV file
        
    Returns:
        Tuple of (PCM data, sample rate)
    """
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        pcm_data = wf.readframes(wf.getnframes())
        
        return pcm_data, sample_rate

def write_wave(path, audio, sample_rate):
    """
    Write PCM data to a WAV file
    
    Args:
        path: Output path
        audio: Audio data (numpy array)
        sample_rate: Sample rate
    """
    # Convert float to int16 if needed
    if audio.dtype != np.int16:
        audio = (audio * 32768).astype(np.int16)
    
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

class Frame(object):
    """
    Represents a "frame" of audio data
    """
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration

def frame_generator(frame_duration_ms, audio, sample_rate):
    """
    Generate audio frames from PCM data
    
    Args:
        frame_duration_ms: Duration of each frame in milliseconds
        audio: PCM audio data
        sample_rate: Sample rate of audio
        
    Returns:
        Generator that yields Frames
    """
    if isinstance(audio, np.ndarray):
        # Convert numpy array to bytes
        audio = (audio * 32768).astype(np.int16).tobytes()
    
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n <= len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n

def vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, vad,
                 frames):
    """
    Filter frames using voice activity detection
    
    Args:
        sample_rate: Audio sample rate
        frame_duration_ms: Frame duration in milliseconds
        padding_duration_ms: Padding duration in milliseconds
        vad: WebRTC VAD instance
        frames: Audio frames
        
    Returns:
        Generator that yields segments of audio where speech is detected
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []

    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])

def convert_sample_rate(audio_path, target_sample_rate=16000):
    """
    Convert an audio file to the target sample rate
    
    Args:
        audio_path: Path to audio file
        target_sample_rate: Target sample rate
        
    Returns:
        Path to the converted audio file
    """
    import librosa
    import soundfile as sf
    import tempfile
    import os
    
    # Load the audio file
    y, sr = librosa.load(audio_path, sr=target_sample_rate)
    
    # Create a temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    
    # Save with the target sample rate
    sf.write(temp_path, y, target_sample_rate)
    
    return temp_path
