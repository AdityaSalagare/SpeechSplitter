import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)

def extract_mfcc(audio, sample_rate, n_mfcc=13, n_fft=512, hop_length=160):
    """
    Extract MFCC features from an audio signal
    
    Args:
        audio: Audio signal as numpy array
        sample_rate: Sample rate of the audio
        n_mfcc: Number of MFCC coefficients to extract
        n_fft: FFT window size
        hop_length: Hop length for FFT
        
    Returns:
        MFCC features as numpy array
    """
    try:
        # Ensure audio is not empty
        if len(audio) == 0:
            logger.warning("Empty audio provided to MFCC extraction")
            return np.array([])
        
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(
            y=audio, 
            sr=sample_rate, 
            n_mfcc=n_mfcc,
            n_fft=n_fft,
            hop_length=hop_length
        )
        
        # Add delta features
        delta_mfcc = librosa.feature.delta(mfccs)
        delta2_mfcc = librosa.feature.delta(mfccs, order=2)
        
        # Concatenate features
        combined_features = np.vstack([mfccs, delta_mfcc, delta2_mfcc])
        
        # Transpose to have time as first dimension
        combined_features = combined_features.T
        
        return combined_features
    
    except Exception as e:
        logger.error(f"Error extracting MFCC features: {e}")
        return np.array([])

def extract_energy(audio, n_fft=512, hop_length=160):
    """
    Extract energy features from an audio signal
    
    Args:
        audio: Audio signal as numpy array
        n_fft: FFT window size
        hop_length: Hop length for FFT
        
    Returns:
        Energy features as numpy array
    """
    try:
        # Compute short-time Fourier transform
        S = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop_length))
        
        # Compute energy
        energy = np.sum(S**2, axis=0)
        
        return energy
    
    except Exception as e:
        logger.error(f"Error extracting energy features: {e}")
        return np.array([])

def extract_features(audio, sample_rate):
    """
    Extract all features for speaker diarization
    
    Args:
        audio: Audio signal as numpy array
        sample_rate: Sample rate of the audio
        
    Returns:
        Dictionary of features
    """
    try:
        # Extract MFCC features
        mfcc = extract_mfcc(audio, sample_rate)
        
        # Extract energy features
        energy = extract_energy(audio)
        
        # Return features
        return {
            'mfcc': mfcc,
            'energy': energy
        }
    
    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        return {
            'mfcc': np.array([]),
            'energy': np.array([])
        }
