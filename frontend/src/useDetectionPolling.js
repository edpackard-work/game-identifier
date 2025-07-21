import { useState, useEffect, useRef } from 'react';
import { processFrame } from './api/identification-api';

const POLLING_INTERVAL_MS = 200;
const TIMEOUT_LIMIT_MS = 20000;

/**
 * Custom hook for polling detection from the backend using a canvas.
 * @param {React.RefObject<HTMLCanvasElement>} canvasRef
 * @param {React.RefObject<HTMLAudioElement>} soundRef
 * @param {React.RefObject<HTMLVideoElement>} videoRef
 * @returns {Object}
 */
export default function useDetectionPolling(canvasRef, soundRef, videoRef) {
  const [detectionResult, setDetectionResult] = useState(null);
  const [error, setError] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [showCaptured, setShowCaptured] = useState(false);
  const [pollingActive, setPollingActive] = useState(true);
  const [timeoutMs, setTimeoutMs] = useState(0);
  const [timedOut, setTimedOut] = useState(false);
  const [backendError, setBackendError] = useState(false);
  const pollingIntervalRef = useRef(null);
  const hiddenCanvasRef = useRef(null);

  useEffect(() => {
    if (!pollingActive || timedOut || backendError) return;
    async function captureAndSendFrame() {
      const video = videoRef.current;
      const hiddenCanvas = hiddenCanvasRef.current;
      if (!video || !hiddenCanvas || video.videoWidth === 0 || video.videoHeight === 0 || video.readyState < 2) {
        // Video not ready yet, skip this polling cycle
        return;
      }
      
      // Draw raw video frame to hidden canvas (no overlays)
      hiddenCanvas.width = video.videoWidth;
      hiddenCanvas.height = video.videoHeight;
      const ctx = hiddenCanvas.getContext('2d');
      ctx.drawImage(video, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
      
      const dataUrl = hiddenCanvas.toDataURL('image/jpeg');
      try {
        const result = await processFrame(dataUrl);
        setDetectionResult(result);
        setError(null);
        if (result.success) {
          setPollingActive(false);
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
          }
          if (soundRef.current) {
            soundRef.current.play();
          }
          setCapturedImage(result.image);
          setShowCaptured(true);
          setTimeoutMs(0);
        } else {
          // Reset timeout if a box is detected, otherwise increment
          if (result.rect) {
            setTimeoutMs(0);
          } else {
            setTimeoutMs(prev => prev + POLLING_INTERVAL_MS);
          }
        }
      } catch {
        setError('There has been a problem');
        setBackendError(true);
        setDetectionResult(null);
        setTimeoutMs(prev => prev + POLLING_INTERVAL_MS);
      }
    }
    pollingIntervalRef.current = setInterval(captureAndSendFrame, POLLING_INTERVAL_MS);
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [pollingActive, timedOut, backendError, canvasRef, soundRef, videoRef]);

  // Detection timeout effect
  useEffect(() => {
    if (timeoutMs >= TIMEOUT_LIMIT_MS && pollingActive) {
      setPollingActive(false);
      setTimedOut(true);
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    }
  }, [timeoutMs, pollingActive]);

  function resetPolling() {
    setDetectionResult(null);
    setError(null);
    setCapturedImage(null);
    setShowCaptured(false);
    setPollingActive(true);
    setTimeoutMs(0);
    setTimedOut(false);
    setBackendError(false);
  }

  return {
    detectionResult,
    error,
    capturedImage,
    showCaptured,
    timedOut,
    backendError,
    resetPolling,
    hiddenCanvasRef,
  };
} 