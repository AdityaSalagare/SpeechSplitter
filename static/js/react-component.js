/**
 * React component for speech diarization
 * - Can be integrated into any React application
 * - Provides recording, processing, and playback functionality
 */

// Define the component (works with either React or Preact)
class SpeechDiarizer extends React.Component {
  constructor(props) {
    super(props);
    
    this.state = {
      isRecording: false,
      isProcessing: false,
      recordingDuration: 0,
      audioUrl: null,
      diarizationResult: null,
      error: null,
      speakers: []
    };
    
    // Configuration
    this.config = {
      apiEndpoint: props.apiEndpoint || '/api/webrtc',
      maxDuration: props.maxDuration || 300, // seconds
      autoProcess: props.autoProcess !== undefined ? props.autoProcess : true,
      showControls: props.showControls !== undefined ? props.showControls : true,
      ...props
    };
    
    // References
    this.recorder = null;
    this.recorderConfig = {
      mimeType: 'audio/webm',
      audioBitsPerSecond: 16000,
      onRecordingStart: this.handleRecordingStart.bind(this),
      onRecordingStop: this.handleRecordingStop.bind(this),
      onRecordingProgress: this.handleRecordingProgress.bind(this),
      onError: this.handleError.bind(this)
    };
    
    // Bind methods
    this.startRecording = this.startRecording.bind(this);
    this.stopRecording = this.stopRecording.bind(this);
    this.processAudio = this.processAudio.bind(this);
    this.reset = this.reset.bind(this);
  }
  
  componentDidMount() {
    // Initialize recorder
    this.recorder = new AudioRecorder(this.recorderConfig);
  }
  
  componentWillUnmount() {
    // Clean up
    if (this.recorder) {
      this.recorder.release();
    }
  }
  
  // Start recording
  async startRecording() {
    this.setState({ error: null });
    
    try {
      await this.recorder.startRecording();
    } catch (error) {
      this.setState({ error: error.message });
    }
  }
  
  // Stop recording
  async stopRecording() {
    if (!this.state.isRecording) return;
    
    try {
      await this.recorder.stopRecording();
    } catch (error) {
      this.setState({ error: error.message });
    }
  }
  
  // Process recorded audio
  async processAudio() {
    this.setState({ isProcessing: true, error: null });
    
    try {
      const result = await this.recorder.uploadWebRTC(this.config.apiEndpoint);
      
      if (result && result.success) {
        // Extract speaker info
        const speakers = Object.keys(result.speakers).map(speakerId => {
          const speakerData = result.speakers[speakerId];
          return {
            id: speakerId,
            audioUrl: `/api/segments/${result.session_id}/${speakerId}`,
            segments: speakerData.segments || [],
            totalDuration: speakerData.total_duration || 0
          };
        });
        
        this.setState({ 
          diarizationResult: result,
          speakers: speakers,
          isProcessing: false
        });
        
        // Call onDiarized callback if provided
        if (this.props.onDiarized) {
          this.props.onDiarized(result, speakers);
        }
      } else {
        throw new Error(result ? result.error : 'Failed to process audio');
      }
    } catch (error) {
      this.setState({ 
        isProcessing: false, 
        error: error.message || 'Error processing audio' 
      });
      
      // Call onError callback if provided
      if (this.props.onError) {
        this.props.onError(error);
      }
    }
  }
  
  // Reset to initial state
  reset() {
    if (this.state.isRecording) {
      this.recorder.cancelRecording();
    }
    
    this.setState({
      isRecording: false,
      isProcessing: false,
      recordingDuration: 0,
      audioUrl: null,
      diarizationResult: null,
      error: null,
      speakers: []
    });
    
    // Call onReset callback if provided
    if (this.props.onReset) {
      this.props.onReset();
    }
  }
  
  // Handle recording start
  handleRecordingStart() {
    this.setState({ 
      isRecording: true,
      recordingDuration: 0,
      audioUrl: null,
      diarizationResult: null,
      error: null,
      speakers: []
    });
    
    // Call onRecordingStart callback if provided
    if (this.props.onRecordingStart) {
      this.props.onRecordingStart();
    }
  }
  
  // Handle recording stop
  handleRecordingStop(result) {
    this.setState({ 
      isRecording: false,
      audioUrl: result.url
    });
    
    // Call onRecordingStop callback if provided
    if (this.props.onRecordingStop) {
      this.props.onRecordingStop(result);
    }
    
    // Auto-process if enabled
    if (this.config.autoProcess) {
      this.processAudio();
    }
  }
  
  // Handle recording progress
  handleRecordingProgress(progress) {
    this.setState({ recordingDuration: progress.duration / 1000 });
    
    // Call onRecordingProgress callback if provided
    if (this.props.onRecordingProgress) {
      this.props.onRecordingProgress(progress);
    }
    
    // Auto-stop if max duration reached
    if (this.config.maxDuration > 0 && 
        progress.duration >= this.config.maxDuration * 1000) {
      this.stopRecording();
    }
  }
  
  // Handle errors
  handleError(error) {
    this.setState({ 
      error: error.message || 'Unknown error',
      isRecording: false,
      isProcessing: false
    });
    
    // Call onError callback if provided
    if (this.props.onError) {
      this.props.onError(error);
    }
  }
  
  // Format time as MM:SS
  formatTime(seconds) {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  }
  
  // Render component
  render() {
    const { isRecording, isProcessing, recordingDuration, 
            audioUrl, diarizationResult, error, speakers } = this.state;
    
    return React.createElement('div', { className: 'speech-diarizer' },
      // Error message
      error && React.createElement('div', { className: 'alert alert-danger' }, error),
      
      // Controls section
      this.config.showControls && React.createElement('div', { className: 'diarizer-controls mb-3' },
        // Record button
        React.createElement('button', {
          className: `btn ${isRecording ? 'btn-danger' : 'btn-primary'} me-2`,
          onClick: isRecording ? this.stopRecording : this.startRecording,
          disabled: isProcessing
        }, isRecording ? 'Stop Recording' : 'Start Recording'),
        
        // Process button (if not auto-processing)
        !this.config.autoProcess && audioUrl && !isRecording && 
        React.createElement('button', {
          className: 'btn btn-success me-2',
          onClick: this.processAudio,
          disabled: isProcessing
        }, 'Process Audio'),
        
        // Reset button
        (audioUrl || diarizationResult) && 
        React.createElement('button', {
          className: 'btn btn-secondary',
          onClick: this.reset,
          disabled: isProcessing
        }, 'Reset'),
        
        // Recording time
        isRecording && 
        React.createElement('span', { className: 'recording-time ms-3' },
          React.createElement('span', { className: 'recording-indicator me-2' }, '🔴'),
          `Recording: ${this.formatTime(recordingDuration)}`
        ),
        
        // Processing indicator
        isProcessing && 
        React.createElement('div', { className: 'spinner-border text-primary ms-3', role: 'status' },
          React.createElement('span', { className: 'visually-hidden' }, 'Processing...')
        )
      ),
      
      // Original audio player
      audioUrl && !isRecording && !isProcessing && !diarizationResult && 
      React.createElement('div', { className: 'original-audio mb-3' },
        React.createElement('h5', {}, 'Recorded Audio:'),
        React.createElement('audio', {
          className: 'w-100',
          controls: true,
          src: audioUrl
        })
      ),
      
      // Diarization results
      diarizationResult && !isRecording && !isProcessing && 
      React.createElement('div', { className: 'diarization-results' },
        React.createElement('h5', {}, `Diarization Results (${speakers.length} speakers):`),
        
        // Speakers
        speakers.map(speaker => 
          React.createElement('div', { 
            className: 'speaker-segment card mb-3', 
            key: speaker.id 
          },
            // Card header
            React.createElement('div', { className: 'card-header' },
              React.createElement('h5', { className: 'mb-0' }, 
                speaker.id.replace('_', ' ')
              )
            ),
            
            // Card body
            React.createElement('div', { className: 'card-body' },
              // Audio player
              React.createElement('audio', {
                className: 'w-100',
                controls: true,
                src: speaker.audioUrl
              }),
              
              // Segments
              speaker.segments.length > 0 && 
              React.createElement('div', { className: 'segments-info mt-2' },
                React.createElement('h6', {}, 'Segments:'),
                React.createElement('ul', { className: 'list-group' },
                  speaker.segments.map((segment, index) => 
                    React.createElement('li', { 
                      className: 'list-group-item d-flex justify-content-between',
                      key: index
                    },
                      React.createElement('span', {}, 
                        `${this.formatTime(segment.start)} - ${this.formatTime(segment.end)}`
                      ),
                      React.createElement('span', { className: 'badge bg-primary rounded-pill' }, 
                        `${segment.duration.toFixed(1)}s`
                      )
                    )
                  )
                )
              )
            )
          )
        )
      )
    );
  }
}

// Usage example:
// <div id="diarizer-container"></div>
// <script>
//   ReactDOM.render(
//     React.createElement(SpeechDiarizer, {
//       apiEndpoint: '/api/webrtc',
//       maxDuration: 60,
//       autoProcess: true,
//       onDiarized: function(result) { console.log('Diarization complete:', result); }
//     }),
//     document.getElementById('diarizer-container')
//   );
// </script>
