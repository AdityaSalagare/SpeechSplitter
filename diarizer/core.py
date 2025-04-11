import os
import uuid
import numpy as np
import librosa
import webrtcvad
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
import logging
from threading import Lock
import tempfile
import wave
import io
from .feature_extraction import extract_mfcc
from .audio_utils import vad_collector, write_wave

logger = logging.getLogger(__name__)

class Diarizer:
    """
    Main diarization class that handles:
    - Processing audio to detect speech segments
    - Identifying different speakers using MFCC features
    - Separating audio into speaker-specific segments
    """
    
    def __init__(self, sample_rate=16000, frame_duration_ms=30, 
                 vad_aggressiveness=3, min_speech_duration_ms=300):
        """
        Initialize the diarizer with audio parameters
        
        Args:
            sample_rate: Audio sample rate in Hz
            frame_duration_ms: Frame duration in milliseconds
            vad_aggressiveness: VAD aggressiveness (0-3)
            min_speech_duration_ms: Minimum speech duration to consider
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.vad_aggressiveness = vad_aggressiveness
        self.min_speech_duration_ms = min_speech_duration_ms
        self.vad = webrtcvad.Vad(self.vad_aggressiveness)
        self.lock = Lock()  # For thread safety
        self.temp_dir = tempfile.mkdtemp()
        logger.debug(f"Initialized Diarizer with sample_rate={sample_rate}, vad_aggressiveness={vad_aggressiveness}")
    
    def process_audio_file(self, file_path):
        """
        Process an audio file for diarization
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary with diarization results
        """
        logger.debug(f"Processing audio file: {file_path}")
        
        # Load audio file and convert to mono if needed
        y, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
        
        # Process the audio
        return self._process_audio(y, sr)
    
    def process_audio_bytes(self, audio_bytes):
        """
        Process audio from bytes for diarization
        
        Args:
            audio_bytes: Audio data as bytes
            
        Returns:
            Dictionary with diarization results
        """
        logger.debug(f"Processing audio bytes, size: {len(audio_bytes)}")
        
        # Convert bytes to numpy array
        with io.BytesIO(audio_bytes) as buf:
            with wave.open(buf, 'rb') as wf:
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                data = wf.readframes(n_frames)
                y = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Process the audio
        return self._process_audio(y, sample_rate)
    
    def _process_audio(self, y, sr):
        """
        Internal method to process audio data
        
        Args:
            y: Audio data as numpy array
            sr: Sample rate
            
        Returns:
            Dictionary with diarization results
        """
        with self.lock:  # Ensure thread safety
            # Step 1: Voice activity detection
            audio_segments = self._detect_speech(y, sr)
            
            # Step 2: Extract features from speech segments
            if not audio_segments:
                logger.warning("No speech segments detected")
                return {"success": False, "error": "No speech detected"}
            
            all_features = []
            segment_times = []
            audio_chunks = []
            
            for start_time, end_time, audio_chunk in audio_segments:
                # Extract MFCC features
                if len(audio_chunk) < sr * 0.1:  # Skip very short segments
                    continue
                    
                mfcc_features = extract_mfcc(audio_chunk, sr)
                if mfcc_features.size > 0:
                    all_features.append(np.mean(mfcc_features, axis=0))
                    segment_times.append((start_time, end_time))
                    audio_chunks.append(audio_chunk)
            
            if not all_features:
                logger.warning("No valid features extracted")
                return {"success": False, "error": "Could not extract features"}
            
            # Step 3: Cluster features to identify speakers
            speaker_labels = self._identify_speakers(np.array(all_features))
            
            # Step 4: Generate output segments by speaker
            result = self._generate_speaker_segments(
                speaker_labels, segment_times, audio_chunks, sr
            )
            
            return result
    
    def _detect_speech(self, audio, sample_rate):
        """
        Detect speech segments in audio using WebRTC VAD
        
        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate
            
        Returns:
            List of tuples (start_time, end_time, audio_segment)
        """
        logger.debug("Detecting speech segments")
        
        # Convert float audio to int16
        audio_int16 = (audio * 32768).astype(np.int16)
        
        # Calculate frame size and padding
        frame_size = int(sample_rate * self.frame_duration_ms / 1000)
        
        # Pad the audio to ensure full frames
        padding = frame_size - (len(audio_int16) % frame_size)
        if padding < frame_size:
            audio_int16 = np.pad(audio_int16, (0, padding), 'constant')
        
        # Create frames for VAD
        frames = [audio_int16[i:i+frame_size] for i in range(0, len(audio_int16), frame_size)]
        
        # Use VAD to detect speech
        speech_frames = []
        for i, frame in enumerate(frames):
            is_speech = self.vad.is_speech(frame.tobytes(), sample_rate)
            if is_speech:
                start_sample = i * frame_size
                end_sample = (i + 1) * frame_size
                start_time = start_sample / sample_rate
                end_time = end_sample / sample_rate
                speech_frames.append((start_time, end_time, audio[start_sample:end_sample]))
        
        # Merge adjacent speech frames
        merged_segments = []
        if speech_frames:
            current_start, current_end, current_audio = speech_frames[0]
            current_audio_list = [current_audio]
            
            for start, end, segment_audio in speech_frames[1:]:
                # If this segment starts right after the current one ends
                if abs(start - current_end) < 0.05:  # 50ms threshold
                    # Extend the current segment
                    current_end = end
                    current_audio_list.append(segment_audio)
                else:
                    # Save the current segment and start a new one
                    merged_audio = np.concatenate(current_audio_list)
                    merged_segments.append((current_start, current_end, merged_audio))
                    current_start, current_end, current_audio = start, end, segment_audio
                    current_audio_list = [current_audio]
            
            # Add the last segment
            merged_audio = np.concatenate(current_audio_list)
            merged_segments.append((current_start, current_end, merged_audio))
        
        # Filter segments that are too short
        min_samples = int(self.min_speech_duration_ms * sample_rate / 1000)
        filtered_segments = []
        for start, end, segment_audio in merged_segments:
            if len(segment_audio) >= min_samples:
                filtered_segments.append((start, end, segment_audio))
        
        logger.debug(f"Detected {len(filtered_segments)} speech segments")
        return filtered_segments
    
    def _identify_speakers(self, features, max_speakers=2):
        """
        Identify speakers using clustering on MFCC features
        
        Args:
            features: MFCC features for each segment
            max_speakers: Maximum number of speakers to identify
            
        Returns:
            Array of speaker labels for each segment
        """
        logger.debug(f"Identifying speakers with max_speakers={max_speakers}")
        
        # Determine number of speakers (up to max_speakers)
        n_speakers = min(max_speakers, len(features))
        
        if n_speakers <= 1:
            return np.zeros(len(features), dtype=int)
        
        # Try with KMeans first
        try:
            kmeans = KMeans(n_clusters=n_speakers, random_state=0, n_init=10)
            labels = kmeans.fit_predict(features)
            
            # Check if the clustering seems reasonable (some segments for each speaker)
            unique, counts = np.unique(labels, return_counts=True)
            if len(unique) < n_speakers or any(count < 2 for count in counts):
                # Try Gaussian Mixture Model as backup
                gmm = GaussianMixture(n_components=n_speakers, random_state=0, n_init=10)
                labels = gmm.fit_predict(features)
        except Exception as e:
            logger.error(f"Error during speaker clustering: {e}")
            # Fallback to simple binary classification if clustering fails
            # Use a simple threshold on the first principal component
            from sklearn.decomposition import PCA
            pca = PCA(n_components=1)
            projected = pca.fit_transform(features).flatten()
            median = np.median(projected)
            labels = (projected > median).astype(int)
        
        logger.debug(f"Speaker identification complete, found {len(np.unique(labels))} speakers")
        return labels
    
    def _generate_speaker_segments(self, speaker_labels, segment_times, audio_chunks, sample_rate):
        """
        Generate final output with separated speaker segments
        
        Args:
            speaker_labels: Array of speaker IDs for each segment
            segment_times: List of (start, end) times for each segment
            audio_chunks: List of audio data for each segment
            sample_rate: Sample rate
            
        Returns:
            Dictionary with diarization results
        """
        logger.debug("Generating speaker segments")
        
        # Create a unique output directory
        session_id = str(uuid.uuid4())
        output_path = os.path.join(self.temp_dir, session_id)
        os.makedirs(output_path, exist_ok=True)
        
        # Group segments by speaker
        speaker_segments = {}
        for i, label in enumerate(speaker_labels):
            speaker_id = f"speaker_{label}"
            if speaker_id not in speaker_segments:
                speaker_segments[speaker_id] = []
            
            speaker_segments[speaker_id].append({
                "start": segment_times[i][0],
                "end": segment_times[i][1],
                "audio": audio_chunks[i]
            })
        
        # Create output for each speaker
        output_files = {}
        for speaker_id, segments in speaker_segments.items():
            # Sort segments by start time
            segments.sort(key=lambda x: x["start"])
            
            # Prepare detailed segment info
            segment_info = [{
                "start": segment["start"], 
                "end": segment["end"],
                "duration": segment["end"] - segment["start"]
            } for segment in segments]
            
            # Concatenate audio for this speaker
            speaker_audio = np.concatenate([segment["audio"] for segment in segments])
            
            # Generate output file path
            output_file = os.path.join(output_path, f"{speaker_id}.wav")
            
            # Save the audio file
            audio_int16 = (speaker_audio * 32768).astype(np.int16)
            with wave.open(output_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
            
            output_files[speaker_id] = {
                "file_path": output_file,
                "segments": segment_info,
                "total_duration": sum(s["duration"] for s in segment_info)
            }
        
        logger.debug(f"Generated {len(output_files)} speaker files")
        
        return {
            "success": True,
            "session_id": session_id,
            "num_speakers": len(output_files),
            "speakers": output_files,
            "temp_dir": output_path
        }
