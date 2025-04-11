import os
import wave
import numpy as np
import librosa
import soundfile as sf
import logging
import uuid

logger = logging.getLogger(__name__)

class AudioSegmenter:
    """
    Class for segmenting audio files based on diarization results.
    """
    def __init__(self, output_dir='output', sample_rate=16000):
        """
        Initialize the audio segmenter.
        
        Args:
            output_dir (str): Directory to store output segments
            sample_rate (int): Sample rate for the output files
        """
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        logger.debug(f"Initialized audio segmenter with output dir {output_dir}")
    
    def segment_audio(self, audio_file, diarized_segments):
        """
        Segment an audio file based on diarization results.
        
        Args:
            audio_file (str): Path to the audio file
            diarized_segments (list): List of diarized segments with speaker labels
            
        Returns:
            dict: Dictionary mapping speaker IDs to lists of segment file paths
        """
        try:
            # Load the audio file
            y, sr = librosa.load(audio_file, sr=None)
            
            # Resample if necessary
            if sr != self.sample_rate:
                logger.info(f"Resampling from {sr}Hz to {self.sample_rate}Hz")
                y = librosa.resample(y, orig_sr=sr, target_sr=self.sample_rate)
                sr = self.sample_rate
                
            # Group segments by speaker
            speaker_segments = {}
            
            for segment in diarized_segments:
                speaker = segment['speaker']
                
                if speaker not in speaker_segments:
                    speaker_segments[speaker] = []
                    
                # Calculate start and end samples
                start_sample = int(segment['start_time'] * sr)
                end_sample = int(segment['end_time'] * sr)
                
                # Extract the segment
                segment_audio = y[start_sample:end_sample]
                
                # Generate output filename
                output_filename = os.path.join(
                    self.output_dir, 
                    f"speaker_{speaker}_{uuid.uuid4().hex[:8]}_{segment['start_time']:.2f}_{segment['end_time']:.2f}.wav"
                )
                
                # Save the segment
                sf.write(output_filename, segment_audio, sr)
                
                # Add to the list of segments for this speaker
                speaker_segments[speaker].append({
                    'file': output_filename,
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'duration': segment['end_time'] - segment['start_time']
                })
                
            num_segments = sum(len(segments) for segments in speaker_segments.values())
            logger.info(f"Created {num_segments} audio segments from {len(diarized_segments)} diarized segments")
            
            return speaker_segments
            
        except Exception as e:
            logger.error(f"Error segmenting audio: {str(e)}")
            raise
    
    def combine_speaker_segments(self, speaker_segments, speaker_id):
        """
        Combine all segments from a speaker into a single audio file.
        
        Args:
            speaker_segments (dict): Dictionary mapping speaker IDs to lists of segment file paths
            speaker_id: The speaker ID to combine
            
        Returns:
            str: Path to the combined audio file
        """
        if speaker_id not in speaker_segments:
            logger.warning(f"No segments found for speaker {speaker_id}")
            return None
            
        try:
            # Sort segments by start time
            segments = sorted(speaker_segments[speaker_id], key=lambda x: x['start_time'])
            
            # Load and concatenate segment audio
            combined_audio = np.array([])
            
            for segment in segments:
                segment_audio, sr = librosa.load(segment['file'], sr=self.sample_rate)
                combined_audio = np.append(combined_audio, segment_audio)
                
            # Generate output filename
            output_filename = os.path.join(
                self.output_dir, 
                f"combined_speaker_{speaker_id}_{uuid.uuid4().hex[:8]}.wav"
            )
            
            # Save the combined audio
            sf.write(output_filename, combined_audio, self.sample_rate)
            
            logger.info(f"Combined {len(segments)} segments into {output_filename}")
            
            return output_filename
            
        except Exception as e:
            logger.error(f"Error combining speaker segments: {str(e)}")
            raise
