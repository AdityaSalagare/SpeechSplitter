import os
import wave
import numpy as np
import pyaudio
import uuid
import logging

logger = logging.getLogger(__name__)

class AudioRecorder:
    """
    Class for recording and handling audio streams.
    """
    def __init__(self, 
                 channels=1, 
                 rate=16000, 
                 chunk_size=1024, 
                 format=pyaudio.paInt16,
                 temp_dir='temp'):
        """
        Initialize the audio recorder.
        
        Args:
            channels (int): Number of audio channels (1 for mono, 2 for stereo)
            rate (int): Sampling rate in Hz
            chunk_size (int): Number of frames per buffer
            format: Audio format (from pyaudio constants)
            temp_dir (str): Directory to store temporary audio files
        """
        self.channels = channels
        self.rate = rate
        self.chunk_size = chunk_size
        self.format = format
        self.temp_dir = temp_dir
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
    
    def record(self, duration=5):
        """
        Record audio for a specified duration.
        
        Args:
            duration (int): Recording duration in seconds
            
        Returns:
            str: Path to the recorded audio file
        """
        try:
            # Open stream
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            logger.info("Recording started...")
            
            # Record audio data
            frames = []
            for i in range(0, int(self.rate / self.chunk_size * duration)):
                data = stream.read(self.chunk_size)
                frames.append(data)
                
            logger.info("Recording finished.")
            
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            
            # Generate a unique filename
            filename = os.path.join(self.temp_dir, f"recording_{uuid.uuid4().hex}.wav")
            
            # Save the recorded data as a WAV file
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
                
            logger.info(f"Audio saved to {filename}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error recording audio: {str(e)}")
            raise
    
    def record_stream(self, callback, stop_callback=None, duration=None):
        """
        Start streaming audio with a callback function for real-time processing.
        
        Args:
            callback: Function to call with each audio chunk
            stop_callback: Function that returns True when streaming should stop
            duration: Maximum duration in seconds, None for unlimited
        """
        frames = []
        
        # Define callback function for the streaming
        def stream_callback(in_data, frame_count, time_info, status):
            frames.append(in_data)
            if callback:
                callback(in_data)
                
            if stop_callback and stop_callback():
                return (None, pyaudio.paComplete)
                
            return (None, pyaudio.paContinue)
        
        # Open stream
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=stream_callback
        )
        
        logger.info("Streaming started...")
        
        # Calculate total frames if duration is specified
        if duration:
            import time
            time.sleep(duration)
            stream.stop_stream()
        
        return stream, frames
    
    def save_frames_to_file(self, frames, filename=None):
        """
        Save audio frames to a WAV file.
        
        Args:
            frames: List of audio frame data
            filename: Output file path (optional, will generate if None)
            
        Returns:
            str: Path to the saved audio file
        """
        if filename is None:
            filename = os.path.join(self.temp_dir, f"recording_{uuid.uuid4().hex}.wav")
            
        # Save the recorded data as a WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            
        logger.info(f"Audio saved to {filename}")
        return filename
    
    def load_audio_from_file(self, filename):
        """
        Load audio data from a WAV file.
        
        Args:
            filename (str): Path to the WAV file
            
        Returns:
            tuple: (samples as numpy array, sample rate)
        """
        import librosa
        try:
            # Load the audio file
            samples, sample_rate = librosa.load(filename, sr=None)
            return samples, sample_rate
        except Exception as e:
            logger.error(f"Error loading audio file: {str(e)}")
            raise
    
    def close(self):
        """
        Terminate the PyAudio instance.
        """
        self.audio.terminate()
