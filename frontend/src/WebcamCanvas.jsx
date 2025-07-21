import { useRef, useEffect } from 'react';

/**
 * @param {Object} props
 * @param {Object} props.detectionResult - Detection result for drawing overlays.
 * @param {boolean} props.showCaptured - Whether to hide the canvas (showing captured image instead).
 * @param {boolean} props.timedOut - Whether detection timed out (hide canvas).
 * @param {boolean} props.backendError - Whether a backend error occurred (hide canvas).
 * @param {function(HTMLCanvasElement):void} props.onCanvasReady - Callback to provide canvas ref to parent.
 * @param {function(HTMLVideoElement):void} [props.onVideoReady] - Optional callback to provide video ref to parent.
 */
function WebcamCanvas({ detectionResult, showCaptured, timedOut, backendError, onCanvasReady, onVideoReady }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const streamRef = useRef(null);

  // Expose refs to parent
  useEffect(() => {
    if (onCanvasReady && canvasRef.current) onCanvasReady(canvasRef.current);
    if (onVideoReady && videoRef.current) onVideoReady(videoRef.current);
  }, [onCanvasReady, onVideoReady]);

  useEffect(() => {
    async function setupWebcam() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        streamRef.current = stream;
      } catch (err) {
        console.error(err);
        alert('Could not access webcam.');
      }
    }
    setupWebcam();
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    function drawVideoToCanvas() {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && canvas && video.videoWidth > 0 && video.videoHeight > 0) {
        const ctx = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        // Draw detection overlay
        if (detectionResult && detectionResult.rect) {
          const { x, y, w, h, label, confidence } = detectionResult.rect;
          ctx.beginPath();
          ctx.rect(x, y, w, h);
          let boxColor = 'blue';
          if (typeof detectionResult.boxes_queue_len === 'number' && detectionResult.boxes_queue_len > 0) {
            boxColor = detectionResult.is_sharp ? 'white' : 'red';
          }
          ctx.strokeStyle = boxColor;
          ctx.lineWidth = 2;
          ctx.stroke();
          if (label && confidence !== undefined) {
            ctx.font = '18px Arial';
            ctx.fillStyle = 'blue';
            const text = `${label} (${(confidence * 100).toFixed(1)}%) [${w}x${h}]`;
            const textWidth = ctx.measureText(text).width;
            ctx.fillRect(x, y - 26, textWidth + 10, 24);
            ctx.fillStyle = 'white';
            ctx.fillText(text, x + 5, y - 8);
          }
        }
      }
      animationFrameRef.current = requestAnimationFrame(drawVideoToCanvas);
    }
    drawVideoToCanvas();
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [detectionResult]);

  return (
    <>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        width="640"
        height="480"
        style={{ display: 'none' }}
      ></video>
      <canvas
        ref={canvasRef}
        width="640"
        height="480"
        style={{ display: showCaptured || timedOut || backendError ? 'none' : 'block', margin: '1rem auto' }}
      ></canvas>
    </>
  );
}

export default WebcamCanvas; 