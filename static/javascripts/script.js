/**
 * @type {HTMLVideoElement}
 */
const video = document.getElementById('webcam');
/**
 * @type {HTMLCanvasElement}
 */
const canvas = document.getElementById('canvas');
/**
 * @type {CanvasRenderingContext2D}
 */
const ctx = canvas.getContext('2d');
/**
 * @type {HTMLImageElement}
 */
const capturedImage = document.getElementById('capturedImage');
/**
 * @type {HTMLElement}
 */
const loading = document.getElementById('loading');
/**
 * @type {HTMLButtonElement}
 */
const tryAgainBtn = document.getElementById('tryAgainBtn');
/**
 * @type {HTMLElement}
 */
const gameInfoDiv = document.getElementById('gameInfo');
/**
 * @type {HTMLElement}
 */
const gameJsonEl = document.getElementById('gameJson');
/**
 * @type {HTMLElement}
 */
const warningMsg = document.getElementById('warningMsg');

let stream = null;
/**
 * @type {number}
 */
const POLLING_INTERVAL_MS = 200;
let pollingInterval = null;
let timeoutTimeMs = 0;
let boundedRect = null;
let boxesQueueLen = 0;
let isSharp = false;
let objectedDetected = false;
/**
 * @type {number}
 */
const TIMEOUT_LIMIT_MS = 20000;

/**
 * Initialize the webcam stream and start polling for frames.
 * @returns {Promise<void>}
 */
async function initWebcam() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;

    video.onloadedmetadata = () => {
      canvas.style.display = 'block';
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      drawVideoToCanvas();
    };

    pollingInterval = setInterval(captureAndSendFrame, POLLING_INTERVAL_MS);
  } catch (err) {
    alert('Could not access webcam.');
  }
}

/**
 * Draw the video frame and bounding box to the canvas.
 * @returns {void}
 */
function drawVideoToCanvas() {
  if (stream && video.videoWidth > 0 && video.videoHeight > 0) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    if (boundedRect) {
      const { x, y, h, w, label, confidence } = boundedRect;
      ctx.beginPath();
      ctx.rect(x, y, w, h);
      ctx.strokeStyle =
        boxesQueueLen > 0 ? (isSharp ? 'white' : 'red') : 'blue';
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
  requestAnimationFrame(drawVideoToCanvas);
}

/**
 * Send a POST request to the given route.
 * @param {string} route
 * @param {string} requestBody
 * @returns {Promise<any>} The parsed JSON response
 */
async function apiPost(route, requestBody) {
  const response = await fetch(route, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  });
  return response.json();
}

function updateGameInfo(gameInfo) {
  const {
    isItAVideoGame,
    title,
    system,
    genre,
    publisher,
    releaseYear,
    region,
    labelCode,
  } = gameInfo;
  gameJsonEl.textContent = isItAVideoGame
    ? `Title: ${title}\nSystem: ${system}\nGenre: ${genre}\nPublisher: ${publisher}\nRelease Year: ${releaseYear}\nRegion: ${region}\nLabel Code: ${labelCode}`
    : 'Sorry, this is not a video game!';
  gameInfoDiv.style.display = 'block';
  tryAgainBtn.style.display = 'block';
}

/**
 * Capture a frame, send it to the backend, and handle the response.
 * @returns {Promise<void>}
 */
async function captureAndSendFrame() {
  if (!stream || video.videoWidth === 0) return;

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL('image/jpeg');

  let processFrame;

  try {
    processFrame = await apiPost('/process_frame', { image: dataUrl });

    if (processFrame.success) {
      timeoutTimeMs = 0;
      stopWebcam();
      const soundEffect = document.getElementById('soundEffect');
      soundEffect.play();

      capturedImage.src = `data:image/jpeg;base64,${processFrame.image}`;
      capturedImage.style.display = 'block';

      loading.style.display = 'block';
      const gameInfo = await apiPost('/generate_game_info', {
        image: processFrame.image,
      });
      loading.style.display = 'none';

      if (gameInfo.success) updateGameInfo(gameInfo);
    } else {
      timeoutTimeMs = processFrame.rect
        ? 0
        : timeoutTimeMs + POLLING_INTERVAL_MS;
      isSharp = processFrame.is_sharp;
      boxesQueueLen = processFrame.boxes_queue_len;
      boundedRect = processFrame.rect;
      if (timeoutTimeMs >= TIMEOUT_LIMIT_MS) {
        stopWebcam('Detection timed out');
      }
    }
  } catch (err) {
    console.error(err);
    stopWebcam('There has been an error');
  }
}

/**
 * Stop the webcam stream and optionally display a warning message.
 * @param {string=} warningMessage
 * @returns {void}
 */
function stopWebcam(warningMessage) {
  canvas.style.display = 'none';

  if (pollingInterval) clearInterval(pollingInterval);

  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  if (warningMessage) {
    warningMsg.textContent = warningMessage;
    warningMsg.style.display = 'block';
    tryAgainBtn.style.display = 'block';
  }
}

/**
 * Reset the app UI and state to allow another detection attempt.
 * @returns {void}
 */
function resetApp() {
  capturedImage.style.display = 'none';
  gameInfoDiv.style.display = 'none';
  tryAgainBtn.style.display = 'none';
  gameJsonEl.textContent = '';
  loading.style.display = 'none';
  timeoutTimeMs = 0;
  warningMsg.style.display = 'none';
  initWebcam();
}

initWebcam();
