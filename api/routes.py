import os
import logging
import uuid
import json
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import threading

# Import core modules
from diarization_core.audio_recorder import AudioRecorder
from diarization_core.voice_detector import VoiceDetector
from diarization_core.feature_extractor import FeatureExtractor
from diarization_core.speaker_diarization import SpeakerDiarization
from diarization_core.segmenter import AudioSegmenter
from utils.audio_utils import validate_audio_file, get_file_extension

logger = logging.getLogger(__name__)

# Create blueprint
diarization_blueprint = Blueprint('diarization', __name__)

# Initialize directories
UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp'
OUTPUT_FOLDER = 'output'

for folder in [UPLOAD_FOLDER, TEMP_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# In-memory storage for processing jobs
processing_jobs = {}

@diarization_blueprint.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'message': 'Speech diarization API is running'})

@diarization_blueprint.route('/upload', methods=['POST'])
def upload_audio():
    """
    Upload an audio file for diarization.
    """
    try:
        # Check if a file was included in the request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        
        # Check if a file was selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate the file type
        if not validate_audio_file(file.filename):
            return jsonify({'error': 'Invalid audio file type'}), 400
        
        # Create a secure filename
        filename = secure_filename(file.filename)
        extension = get_file_extension(filename)
        
        # Generate a unique ID for this job
        job_id = str(uuid.uuid4())
        
        # Save the file to the upload folder
        file_path = os.path.join(UPLOAD_FOLDER, f"{job_id}{extension}")
        file.save(file_path)
        
        # Store job information
        processing_jobs[job_id] = {
            'status': 'uploaded',
            'file_path': file_path,
            'original_filename': filename
        }
        
        # Start processing in a background thread
        threading.Thread(
            target=process_audio_file,
            args=(job_id, file_path)
        ).start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'uploaded',
            'message': 'File uploaded successfully, processing started'
        })
        
    except Exception as e:
        logger.error(f"Error uploading audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@diarization_blueprint.route('/record', methods=['POST'])
def record_audio():
    """
    Record audio for diarization.
    """
    try:
        # Get recording duration from the request
        data = request.get_json()
        duration = data.get('duration', 10)  # Default to 10 seconds
        
        # Generate a unique ID for this job
        job_id = str(uuid.uuid4())
        
        # Initialize recorder
        recorder = AudioRecorder(temp_dir=TEMP_FOLDER)
        
        # Record audio
        file_path = recorder.record(duration=duration)
        
        # Store job information
        processing_jobs[job_id] = {
            'status': 'recorded',
            'file_path': file_path,
            'original_filename': os.path.basename(file_path)
        }
        
        # Start processing in a background thread
        threading.Thread(
            target=process_audio_file,
            args=(job_id, file_path)
        ).start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'recorded',
            'message': f'Audio recorded for {duration} seconds, processing started'
        })
        
    except Exception as e:
        logger.error(f"Error recording audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_audio_file(job_id, file_path):
    """
    Process an audio file for diarization.
    
    Args:
        job_id (str): Job ID
        file_path (str): Path to the audio file
    """
    try:
        # Update job status
        processing_jobs[job_id]['status'] = 'processing'
        
        # Initialize components
        recorder = AudioRecorder(temp_dir=TEMP_FOLDER)
        voice_detector = VoiceDetector()
        feature_extractor = FeatureExtractor()
        diarizer = SpeakerDiarization(num_speakers=2)
        segmenter = AudioSegmenter(output_dir=OUTPUT_FOLDER)
        
        # Load audio file
        audio_data, sample_rate = recorder.load_audio_from_file(file_path)
        
        # Detect voice segments
        voice_segments = voice_detector.detect_voice_segments(audio_data, sample_rate)
        
        # Extract features from segments
        feature_segments = feature_extractor.extract_features_from_segments(audio_data, voice_segments, sample_rate)
        
        # Skip diarization if no segments found
        if not feature_segments:
            processing_jobs[job_id]['status'] = 'completed'
            processing_jobs[job_id]['result'] = {
                'error': 'No voice segments detected in the audio'
            }
            return
        
        # Perform diarization
        diarized_segments = diarizer.diarize(feature_segments)
        
        # Merge consecutive segments from the same speaker
        merged_segments = diarizer.merge_consecutive_segments(diarized_segments)
        
        # Segment the audio
        speaker_segments = segmenter.segment_audio(file_path, merged_segments)
        
        # Create combined files for each speaker
        combined_files = {}
        for speaker_id in speaker_segments:
            combined_file = segmenter.combine_speaker_segments(speaker_segments, speaker_id)
            if combined_file:
                combined_files[speaker_id] = combined_file
        
        # Store results
        processing_jobs[job_id]['status'] = 'completed'
        processing_jobs[job_id]['result'] = {
            'num_segments': len(merged_segments),
            'speaker_segments': {
                speaker_id: [
                    {
                        'file': os.path.basename(segment['file']),
                        'start_time': segment['start_time'],
                        'end_time': segment['end_time'],
                        'duration': segment['duration'],
                    }
                    for segment in segments
                ]
                for speaker_id, segments in speaker_segments.items()
            },
            'combined_files': {
                speaker_id: os.path.basename(file_path)
                for speaker_id, file_path in combined_files.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        processing_jobs[job_id]['status'] = 'error'
        processing_jobs[job_id]['error'] = str(e)

@diarization_blueprint.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Get the status of a diarization job.
    """
    try:
        if job_id not in processing_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = processing_jobs[job_id]
        
        response = {
            'job_id': job_id,
            'status': job['status'],
            'original_filename': job['original_filename']
        }
        
        # Include results if processing is complete
        if job['status'] == 'completed' and 'result' in job:
            response['result'] = job['result']
        
        # Include error if there was one
        if job['status'] == 'error' and 'error' in job:
            response['error'] = job['error']
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@diarization_blueprint.route('/download/<file_type>/<filename>', methods=['GET'])
def download_file(file_type, filename):
    """
    Download a processed audio file.
    """
    try:
        if file_type == 'segment':
            file_path = os.path.join(OUTPUT_FOLDER, secure_filename(filename))
        else:
            return jsonify({'error': 'Invalid file type'}), 400
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@diarization_blueprint.route('/stream', methods=['POST'])
def start_streaming():
    """
    Start streaming audio for real-time diarization.
    This is a placeholder for WebSocket-based streaming functionality.
    """
    return jsonify({
        'error': 'Streaming API not yet implemented',
        'message': 'For real-time diarization, please use the WebSocket endpoint /ws/stream'
    }), 501
