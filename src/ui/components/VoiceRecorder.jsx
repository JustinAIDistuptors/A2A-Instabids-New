/**
 * VoiceRecorder component for capturing audio input from the user.
 * Uses the MediaRecorder API to record audio and convert it to base64 for API submission.
 */
import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";

/**
 * Voice recording component with start/stop functionality
 * 
 * @param {Object} props - Component props
 * @param {Function} props.onStop - Callback function that receives the base64-encoded audio when recording stops
 * @returns {JSX.Element} Rendered component
 */
export default function VoiceRecorder({ onStop }) {
  const [rec, setRec] = useState(null);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState(null);
  const mediaRef = useRef(null);

  // Initialize MediaRecorder when component mounts
  useEffect(() => {
    if (!rec && navigator.mediaDevices) {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then((stream) => {
          // Create MediaRecorder instance
          const mr = new MediaRecorder(stream); // MediaRecorder API
          
          // Handle data available event (triggered when recording stops)
          mr.ondataavailable = (e) => {
            const reader = new FileReader();
            reader.onloadend = () => {
              // Extract base64 payload and pass to callback
              const base64Data = reader.result.split(",")[1];
              onStop(base64Data);
            };
            reader.readAsDataURL(e.data);
          };
          
          // Store MediaRecorder reference
          mediaRef.current = mr;
          setRec(mr);
        })
        .catch((err) => {
          console.error("Error accessing microphone:", err);
          setError("Could not access microphone. Please check permissions.");
        });
    }
    
    // Cleanup function to stop recording and release media stream
    return () => {
      if (mediaRef.current && mediaRef.current.state === "recording") {
        mediaRef.current.stop();
      }
      if (mediaRef.current && mediaRef.current.stream) {
        mediaRef.current.stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [rec, onStop]);

  /**
   * Toggle recording state
   */
  const toggle = () => {
    if (!mediaRef.current) return;
    
    if (!recording) {
      // Start recording
      mediaRef.current.start();
    } else {
      // Stop recording
      mediaRef.current.stop();
    }
    
    setRecording(!recording);
  };

  // Show error message if microphone access fails
  if (error) {
    return (
      <div className="text-red-500 text-sm mb-2">
        {error}
      </div>
    );
  }

  return (
    <button 
      onClick={toggle} 
      className={`px-4 py-2 rounded-full flex items-center ${
        recording 
          ? "bg-red-500 hover:bg-red-600" 
          : "bg-blue-500 hover:bg-blue-600"
      } text-white transition-colors`}
      disabled={!rec}
      aria-label={recording ? "Stop recording" : "Start recording"}
    >
      {/* Microphone/Stop icon */}
      <span className="mr-2">
        {recording ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <rect width="10" height="10" x="3" y="3" rx="1" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 5a2 2 0 0 0-2 2v4a2 2 0 1 0 4 0V7a2 2 0 0 0-2-2z" />
            <path d="M5 8a3 3 0 0 1 6 0v2.5c0 .83.67 1.5 1.5 1.5H13a.5.5 0 0 1 0 1h-.5A2.5 2.5 0 0 1 10 10.5V8a2 2 0 1 0-4 0v2.5A2.5 2.5 0 0 1 3.5 13H3a.5.5 0 0 1 0-1h.5c.83 0 1.5-.67 1.5-1.5V8z" />
          </svg>
        )}
      </span>
      {recording ? "Stop" : "Record"}
      
      {/* Recording indicator */}
      {recording && (
        <span className="ml-2 h-2 w-2 rounded-full bg-white animate-pulse"></span>
      )}
    </button>
  );
}

// PropTypes for type checking
VoiceRecorder.propTypes = {
  onStop: PropTypes.func.isRequired
};