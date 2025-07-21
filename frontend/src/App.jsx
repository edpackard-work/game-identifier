import { useRef, useEffect, useState } from 'react';
import { generateGameInfo } from './api/identification-api';
import GameInfoDisplay from './GameInfoDisplay';
import WebcamCanvas from './WebcamCanvas';
import useDetectionPolling from './useDetectionPolling';

function App() {
  const canvasRef = useRef(null);
  const soundRef = useRef(null);
  const videoRef = useRef(null);

  const [loading, setLoading] = useState(false);
  const [gameInfo, setGameInfo] = useState(null);
  const {
    detectionResult,
    error,
    capturedImage,
    showCaptured,
    timedOut,
    backendError,
    resetPolling,
    hiddenCanvasRef,
  } = useDetectionPolling(canvasRef, soundRef, videoRef);

  const handleTryAgain = () => {
    resetPolling();
    setLoading(false);
    setGameInfo(null);
  };

  useEffect(() => {
    async function setupWebcam() {
      try {
        await navigator.mediaDevices.getUserMedia({ video: true });
      } catch (err) {
        console.error(err);
        alert('Could not access webcam.');
      }
    }
    setupWebcam();
    return () => {};
  }, []);

  useEffect(() => {
    async function fetchGameInfo() {
      setLoading(true);
      setGameInfo(null);
      try {
        const info = await generateGameInfo(capturedImage);
        setGameInfo(info);
      } catch (err) {
        setGameInfo(null);
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    if (showCaptured && capturedImage) {
      fetchGameInfo();
    }
  }, [showCaptured, capturedImage]);

  return (
    <div style={{ textAlign: 'center' }}>
      <h1>Retro Game Identifier</h1>
      <div id="container">
        <WebcamCanvas
          detectionResult={detectionResult}
          showCaptured={showCaptured}
          timedOut={timedOut}
          backendError={backendError}
          onCanvasReady={ref => { canvasRef.current = ref; }}
          onVideoReady={ref => { videoRef.current = ref; }}
        />
        <canvas
          ref={hiddenCanvasRef}
          style={{ display: 'none' }}
        />
        <img
          id="capturedImage"
          alt="Captured"
          style={{ display: showCaptured ? 'block' : 'none', margin: '1rem auto' }}
          src={showCaptured && capturedImage ? `data:image/jpeg;base64,${capturedImage}` : null}
        />
        <audio src="/sounds/shutter.wav" id="soundEffect" ref={soundRef}></audio>
      </div>
      {loading && (
        <div id="loading" style={{ textAlign: 'center', display: 'block' }}>Loading game info...</div>
      )}
      {gameInfo && (
        <div id="gameInfo" style={{ textAlign: 'center' }}>
          <h2>Game Info</h2>
          <GameInfoDisplay gameInfo={gameInfo} />
        </div>
      )}
      {timedOut && (
        <div style={{ color: 'red', margin: '1rem' }}>Detection timed out. Please try again.</div>
      )}
      <button
        id="tryAgainBtn"
        style={{ display: (gameInfo || timedOut || backendError) ? 'inline-block' : 'none', margin: '1rem' }}
        onClick={handleTryAgain}
      >
        Try Again
      </button>
      {error && <div style={{ color: 'red' }}>{error}</div>}
    </div>
  );
}

export default App;
