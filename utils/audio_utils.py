import os
import logging

logger = logging.getLogger(__name__)

def validate_audio_file(filename):
    """
    Validate that a file is an allowed audio type.
    
    Args:
        filename (str): The name of the file to validate
        
    Returns:
        bool: True if the file is an allowed audio type, False otherwise
    """
    allowed_extensions = {'wav', 'mp3', 'ogg', 'flac', 'm4a'}
    extension = get_file_extension(filename).lower().lstrip('.')
    
    return extension in allowed_extensions

def get_file_extension(filename):
    """
    Get the extension of a file.
    
    Args:
        filename (str): The name of the file
        
    Returns:
        str: The file extension (including the dot)
    """
    _, extension = os.path.splitext(filename)
    return extension

def format_time(seconds):
    """
    Format a time in seconds to a readable string.
    
    Args:
        seconds (float): Time in seconds
        
    Returns:
        str: Formatted time string (MM:SS)
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def get_audio_duration(file_path):
    """
    Get the duration of an audio file.
    
    Args:
        file_path (str): Path to the audio file
        
    Returns:
        float: Duration in seconds, or None if an error occurs
    """
    try:
        import librosa
        y, sr = librosa.load(file_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        return duration
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        return None

def ensure_mono(y, sr):
    """
    Ensure audio is mono channel.
    
    Args:
        y (numpy.ndarray): Audio data
        sr (int): Sample rate
        
    Returns:
        numpy.ndarray: Mono audio data
    """
    import librosa
    if len(y.shape) > 1:
        y = librosa.to_mono(y)
    return y
