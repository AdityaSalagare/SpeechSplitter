/**
 * Audio recorder component for speech diarization
 * Uses the MediaRecorder API to record audio from the user's microphone
 */
class DiarizationRecorder {
    constructor(options = {}) {
        // Default options
        this.options = {
            audioBitsPerSecond: 16000,
            mimeType: 'audio/webm',
            ...options
        };
        
        // State variables
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        this.isRecording = false;
        this.onDataAvailableCallback = null;
        this.onStopCallback = null;
        this.onStartCallback = null;
        this.onErrorCallback = null;
    }
    
    /**
     * Request microphone access and initialize the recorder
     */
    async init() {
        try {
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: true,
                video: false
            });
            
            // Check for supported mime types
            const mimeType = this.getSupportedMimeType();
            
            // Create MediaRecorder instance
            this.mediaRecorder = new MediaRecorder(this.stream, {
                audioBitsPerSecond: this.options.audioBitsPerSecond,
                mimeType
            });
            
            // Set up event handlers
            this.mediaRecorder.ondataavailable = this.handleDataAvailable.bind(this);
            this.mediaRecorder.onstop = this.handleStop.bind(this);
            this.mediaRecorder.onstart = this.handleStart.bind(this);
            this.mediaRecorder.onerror = this.handleError.bind(this);
            
            return true;
        } catch (error) {
            console.error('Error initializing recorder:', error);
            if (this.onErrorCallback) this.onErrorCallback(error);
            return false;
        }
    }
    
    /**
     * Find a supported mime type for audio recording
     */
    getSupportedMimeType() {
        const types = [
            'audio/webm',
            'audio/webm;codecs=opus',
            'audio/ogg;codecs=opus',
            'audio/mp4'
        ];
        
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                console.log(`Using mime type: ${type}`);
                return type;
            }
        }
        
        // Fallback
        return '';
    }
    
    /**
     * Start recording
     * @param {number} timeslice - Optional timeslice in ms for ondataavailable events
     */
    start(timeslice = undefined) {
        if (!this.mediaRecorder) {
            console.error('Recorder not initialized. Call init() first.');
            return false;
        }
        
        if (this.isRecording) {
            console.warn('Already recording.');
            return false;
        }
        
        // Reset chunks array
        this.audioChunks = [];
        
        // Start recording
        try {
            this.mediaRecorder.start(timeslice);
            this.isRecording = true;
            return true;
        } catch (error) {
            console.error('Error starting recording:', error);
            if (this.onErrorCallback) this.onErrorCallback(error);
            return false;
        }
    }
    
    /**
     * Stop recording
     */
    stop() {
        if (!this.mediaRecorder || !this.isRecording) {
            console.warn('Not recording.');
            return false;
        }
        
        try {
            this.mediaRecorder.stop();
            this.isRecording = false;
            return true;
        } catch (error) {
            console.error('Error stopping recording:', error);
            if (this.onErrorCallback) this.onErrorCallback(error);
            return false;
        }
    }
    
    /**
     * Pause recording (if supported)
     */
    pause() {
        if (!this.mediaRecorder || !this.isRecording) {
            return false;
        }
        
        try {
            if (this.mediaRecorder.state === 'recording') {
                this.mediaRecorder.pause();
                return true;
            }
        } catch (error) {
            console.error('Error pausing recording:', error);
            return false;
        }
        
        return false;
    }
    
    /**
     * Resume recording (if paused)
     */
    resume() {
        if (!this.mediaRecorder) {
            return false;
        }
        
        try {
            if (this.mediaRecorder.state === 'paused') {
                this.mediaRecorder.resume();
                return true;
            }
        } catch (error) {
            console.error('Error resuming recording:', error);
            return false;
        }
        
        return false;
    }
    
    /**
     * Clean up resources
     */
    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        this.mediaRecorder = null;
        this.isRecording = false;
        this.audioChunks = [];
    }
    
    /**
     * Get recorded audio as a Blob
     * @returns {Blob} Audio blob
     */
    getAudioBlob() {
        const mimeType = this.mediaRecorder ? this.mediaRecorder.mimeType : this.options.mimeType;
        return new Blob(this.audioChunks, { type: mimeType });
    }
    
    /**
     * Get recorded audio as a File object
     * @param {string} filename - Name for the file
     * @returns {File} Audio file
     */
    getAudioFile(filename = 'recording.webm') {
        const blob = this.getAudioBlob();
        return new File([blob], filename, { type: blob.type });
    }
    
    /**
     * Create an audio URL for playback
     * @returns {string} Audio URL
     */
    getAudioURL() {
        const blob = this.getAudioBlob();
        return URL.createObjectURL(blob);
    }
    
    /**
     * Handle data available event
     * @param {Event} event - Media recorder event
     */
    handleDataAvailable(event) {
        if (event.data.size > 0) {
            this.audioChunks.push(event.data);
            
            if (this.onDataAvailableCallback) {
                this.onDataAvailableCallback(event.data);
            }
        }
    }
    
    /**
     * Handle recording stopped event
     * @param {Event} event - Media recorder event
     */
    handleStop(event) {
        console.log('Recording stopped');
        
        if (this.onStopCallback) {
            const blob = this.getAudioBlob();
            this.onStopCallback(blob, this.getAudioURL());
        }
    }
    
    /**
     * Handle recording started event
     * @param {Event} event - Media recorder event
     */
    handleStart(event) {
        console.log('Recording started');
        
        if (this.onStartCallback) {
            this.onStartCallback();
        }
    }
    
    /**
     * Handle recording error event
     * @param {Event} event - Media recorder event
     */
    handleError(event) {
        console.error('Recording error:', event.error);
        
        if (this.onErrorCallback) {
            this.onErrorCallback(event.error);
        }
    }
    
    /**
     * Set callback for data available event
     * @param {Function} callback - Function to call when data is available
     */
    onDataAvailable(callback) {
        this.onDataAvailableCallback = callback;
        return this;
    }
    
    /**
     * Set callback for recording stopped event
     * @param {Function} callback - Function to call when recording stops
     */
    onStop(callback) {
        this.onStopCallback = callback;
        return this;
    }
    
    /**
     * Set callback for recording started event
     * @param {Function} callback - Function to call when recording starts
     */
    onStart(callback) {
        this.onStartCallback = callback;
        return this;
    }
    
    /**
     * Set callback for error event
     * @param {Function} callback - Function to call when an error occurs
     */
    onError(callback) {
        this.onErrorCallback = callback;
        return this;
    }
}
