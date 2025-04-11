/**
 * Audio recorder for speech diarization demo
 * - Uses Web Audio API to record audio
 * - Handles audio processing and uploading to the API
 */

class AudioRecorder {
  constructor(options = {}) {
    this.audioContext = null;
    this.stream = null;
    this.recorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.durationMs = 0;
    this.startTime = 0;
    
    // Configuration
    this.config = {
      mimeType: 'audio/webm',
      audioBitsPerSecond: 16000,
      ...options
    };
    
    // Callbacks
    this.onRecordingStart = options.onRecordingStart || (() => {});
    this.onRecordingStop = options.onRecordingStop || (() => {});
    this.onRecordingProgress = options.onRecordingProgress || (() => {});
    this.onError = options.onError || ((error) => console.error('Recording error:', error));
    
    // Timer for progress updates
    this.progressTimer = null;
    
    // Bind methods
    this.startRecording = this.startRecording.bind(this);
    this.stopRecording = this.stopRecording.bind(this);
    this.cancelRecording = this.cancelRecording.bind(this);
    this._updateProgress = this._updateProgress.bind(this);
    
    // Check for browser support
    if (!this._checkBrowserSupport()) {
      this.onError(new Error('Browser does not support audio recording'));
    }
  }
  
  /**
   * Check if browser supports required APIs
   */
  _checkBrowserSupport() {
    return !!(navigator.mediaDevices && 
              navigator.mediaDevices.getUserMedia && 
              window.MediaRecorder && 
              window.AudioContext);
  }
  
  /**
   * Initialize audio context and request permissions
   */
  async initialize() {
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      return true;
    } catch (error) {
      this.onError(error);
      return false;
    }
  }
  
  /**
   * Start recording audio
   */
  async startRecording() {
    if (this.isRecording) {
      return false;
    }
    
    try {
      // Initialize if not already done
      if (!this.stream) {
        await this.initialize();
      }
      
      // Reset state
      this.audioChunks = [];
      this.durationMs = 0;
      this.startTime = Date.now();
      
      // Create MediaRecorder
      this.recorder = new MediaRecorder(this.stream, this.config);
      
      // Set up event handlers
      this.recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };
      
      this.recorder.onstop = () => {
        this.isRecording = false;
        this.durationMs = Date.now() - this.startTime;
        clearInterval(this.progressTimer);
        
        // Create result blob
        const audioBlob = new Blob(this.audioChunks, { type: this.config.mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Call callback with results
        this.onRecordingStop({
          blob: audioBlob,
          url: audioUrl,
          duration: this.durationMs
        });
      };
      
      // Start recording
      this.recorder.start(100); // Collect data every 100ms
      this.isRecording = true;
      
      // Start progress timer
      this.progressTimer = setInterval(this._updateProgress, 100);
      
      // Call callback
      this.onRecordingStart();
      
      return true;
    } catch (error) {
      this.onError(error);
      return false;
    }
  }
  
  /**
   * Stop recording and process audio
   */
  stopRecording() {
    if (!this.isRecording || !this.recorder) {
      return false;
    }
    
    try {
      this.recorder.stop();
      return true;
    } catch (error) {
      this.onError(error);
      return false;
    }
  }
  
  /**
   * Cancel recording without processing
   */
  cancelRecording() {
    if (!this.isRecording || !this.recorder) {
      return false;
    }
    
    try {
      this.recorder.stop();
      this.audioChunks = [];
      return true;
    } catch (error) {
      this.onError(error);
      return false;
    }
  }
  
  /**
   * Release resources
   */
  release() {
    if (this.isRecording) {
      this.cancelRecording();
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    clearInterval(this.progressTimer);
  }
  
  /**
   * Upload recorded audio to the API
   */
  async uploadRecording(apiEndpoint = '/api/upload') {
    if (this.isRecording || this.audioChunks.length === 0) {
      return null;
    }
    
    try {
      const audioBlob = new Blob(this.audioChunks, { type: this.config.mimeType });
      
      // Create form data
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      
      // Upload to API
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      this.onError(error);
      return null;
    }
  }
  
  /**
   * Upload audio for WebRTC streaming
   */
  async uploadWebRTC(apiEndpoint = '/api/webrtc') {
    if (this.isRecording || this.audioChunks.length === 0) {
      return null;
    }
    
    try {
      const audioBlob = new Blob(this.audioChunks, { type: this.config.mimeType });
      
      // Create form data
      const formData = new FormData();
      formData.append('audio', audioBlob);
      
      // Upload to API
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      this.onError(error);
      return null;
    }
  }
  
  /**
   * Update recording progress
   */
  _updateProgress() {
    if (!this.isRecording) {
      return;
    }
    
    const currentTime = Date.now();
    this.durationMs = currentTime - this.startTime;
    
    this.onRecordingProgress({
      duration: this.durationMs,
      chunks: this.audioChunks.length
    });
  }
}

/**
 * Audio player for diarized segments
 */
class DiarizedAudioPlayer {
  constructor(elementId, options = {}) {
    this.container = document.getElementById(elementId);
    this.players = {};
    this.currentSession = null;
    
    // Configuration
    this.config = {
      maxDuration: 300000, // 5 minutes max
      ...options
    };
    
    // Bind methods
    this.displayResults = this.displayResults.bind(this);
    this.clearResults = this.clearResults.bind(this);
  }
  
  /**
   * Display diarization results
   */
  displayResults(diarizationResult) {
    this.clearResults();
    
    if (!diarizationResult || !diarizationResult.success) {
      this.showError('No valid diarization results to display');
      return;
    }
    
    this.currentSession = diarizationResult.session_id;
    
    // Create container for results
    const resultsDiv = document.createElement('div');
    resultsDiv.className = 'diarization-results mt-4';
    
    // Add header
    const header = document.createElement('h3');
    header.textContent = `Diarization Results (${diarizationResult.num_speakers} speakers)`;
    resultsDiv.appendChild(header);
    
    // Add speaker segments
    Object.keys(diarizationResult.speakers).forEach(speakerId => {
      const speakerData = diarizationResult.speakers[speakerId];
      
      // Create speaker container
      const speakerDiv = document.createElement('div');
      speakerDiv.className = 'speaker-segment card mt-3';
      
      // Create card header
      const cardHeader = document.createElement('div');
      cardHeader.className = 'card-header d-flex justify-content-between align-items-center';
      
      // Add speaker label
      const speakerLabel = document.createElement('h5');
      speakerLabel.className = 'mb-0';
      speakerLabel.textContent = speakerId.replace('_', ' ');
      cardHeader.appendChild(speakerLabel);
      
      // Add total duration
      const durationLabel = document.createElement('span');
      durationLabel.className = 'text-muted';
      durationLabel.textContent = this.formatDuration(speakerData.total_duration);
      cardHeader.appendChild(durationLabel);
      
      speakerDiv.appendChild(cardHeader);
      
      // Create card body
      const cardBody = document.createElement('div');
      cardBody.className = 'card-body';
      
      // Add audio player
      const audioPlayer = document.createElement('audio');
      audioPlayer.controls = true;
      audioPlayer.className = 'w-100';
      audioPlayer.src = `/api/segments/${diarizationResult.session_id}/${speakerId}`;
      cardBody.appendChild(audioPlayer);
      
      // Store reference to player
      this.players[speakerId] = audioPlayer;
      
      // Add segments timeline if available
      if (speakerData.segments && speakerData.segments.length > 0) {
        const timelineDiv = document.createElement('div');
        timelineDiv.className = 'segments-timeline mt-3';
        
        // Add timeline header
        const timelineHeader = document.createElement('h6');
        timelineHeader.textContent = 'Speech Segments:';
        timelineDiv.appendChild(timelineHeader);
        
        // Add timeline visualization
        const timeline = document.createElement('div');
        timeline.className = 'timeline-viz mt-2';
        
        speakerData.segments.forEach((segment, index) => {
          const segmentEl = document.createElement('div');
          segmentEl.className = 'segment-item';
          segmentEl.innerHTML = `
            <span class="segment-time">${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}</span>
            <span class="segment-duration">(${this.formatDuration(segment.duration)})</span>
          `;
          timeline.appendChild(segmentEl);
        });
        
        timelineDiv.appendChild(timeline);
        cardBody.appendChild(timelineDiv);
      }
      
      speakerDiv.appendChild(cardBody);
      resultsDiv.appendChild(speakerDiv);
    });
    
    // Add to container
    this.container.appendChild(resultsDiv);
  }
  
  /**
   * Clear displayed results
   */
  clearResults() {
    // Stop any playing audio
    Object.values(this.players).forEach(player => {
      player.pause();
      player.currentTime = 0;
    });
    
    // Clear players
    this.players = {};
    this.currentSession = null;
    
    // Clear container
    this.container.innerHTML = '';
  }
  
  /**
   * Show error message
   */
  showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger mt-3';
    errorDiv.textContent = message;
    this.container.appendChild(errorDiv);
  }
  
  /**
   * Format time as MM:SS.MS
   */
  formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms}`;
  }
  
  /**
   * Format duration in seconds as human-readable
   */
  formatDuration(seconds) {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    
    const minutes = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    
    return `${minutes}m ${secs}s`;
  }
}
