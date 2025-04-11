import os
import tempfile
import json
import logging
from flask import Blueprint, request, jsonify, send_file, render_template, Response
from werkzeug.utils import secure_filename
import uuid
from diarizer import Diarizer

# Create Blueprint
api_bp = Blueprint('api', __name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize diarizer
diarizer = Diarizer()

# Helper functions
def allowed_file(filename):
    """Check if file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac', 'webm'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    API endpoint to upload an audio file for diarization
    
    Returns:
        JSON response with diarization results
    """
    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    
    # Check if file is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file has allowed extension
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Save file to temporary location
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(file_path)
        
        # Process audio file
        result = diarizer.process_audio_file(file_path)
        
        # Clean up
        os.remove(file_path)
        os.rmdir(temp_dir)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/stream', methods=['POST'])
def process_stream():
    """
    API endpoint to process streamed audio data
    
    Returns:
        JSON response with diarization results
    """
    try:
        # Get audio data from request
        audio_data = request.data
        
        if not audio_data:
            return jsonify({'error': 'No audio data received'}), 400
        
        # Process audio data
        result = diarizer.process_audio_bytes(audio_data)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing audio stream: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/segments/<session_id>/<speaker_id>', methods=['GET'])
def get_speaker_segment(session_id, speaker_id):
    """
    API endpoint to get audio segments for a specific speaker
    
    Args:
        session_id: Diarization session ID
        speaker_id: Speaker ID
        
    Returns:
        Audio file for the speaker
    """
    try:
        # Construct file path
        temp_dir = os.path.join(diarizer.temp_dir, session_id)
        file_path = os.path.join(temp_dir, f"{speaker_id}.wav")
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'Speaker segment not found'}), 404
        
        # Return audio file
        return send_file(file_path, mimetype='audio/wav')
    
    except Exception as e:
        logger.error(f"Error retrieving speaker segment: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/info/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """
    API endpoint to get information about a diarization session
    
    Args:
        session_id: Diarization session ID
        
    Returns:
        JSON with session information
    """
    try:
        # Construct directory path
        temp_dir = os.path.join(diarizer.temp_dir, session_id)
        
        # Check if directory exists
        if not os.path.exists(temp_dir):
            return jsonify({'error': 'Session not found'}), 404
        
        # Get list of speaker files
        speaker_files = [f for f in os.listdir(temp_dir) if f.endswith('.wav')]
        
        # Create response with speaker info
        speakers = {}
        for speaker_file in speaker_files:
            speaker_id = os.path.splitext(speaker_file)[0]
            speakers[speaker_id] = {
                'url': f'/api/segments/{session_id}/{speaker_id}'
            }
        
        return jsonify({
            'session_id': session_id,
            'num_speakers': len(speaker_files),
            'speakers': speakers
        })
    
    except Exception as e:
        logger.error(f"Error retrieving session info: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/webrtc', methods=['POST'])
def process_webrtc():
    """
    API endpoint to process audio from WebRTC
    
    Returns:
        JSON response with diarization results
    """
    try:
        # Get audio data from request
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio data received'}), 400
        
        audio_file = request.files['audio']
        
        # Save file to temporary location
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
        audio_file.save(file_path)
        
        # Process audio file
        result = diarizer.process_audio_file(file_path)
        
        # Clean up
        os.remove(file_path)
        os.rmdir(temp_dir)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing WebRTC audio: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})
