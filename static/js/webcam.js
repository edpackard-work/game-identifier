import { ELEMENT_IDS, getEl, show, hide } from './dom.js';
import { apiPost } from './api.js';
import { gameInfoString } from './gameInfo.js';

/**
 * @type {number}
 */
const TIMEOUT_LIMIT_MS = 20000;
/**
 * @type {number}
 */
const POLLING_INTERVAL_MS = 200;

/** @type {HTMLVideoElement} */
const video = getEl(ELEMENT_IDS.video, HTMLVideoElement);
/** @type {HTMLCanvasElement} */
const canvas = getEl(ELEMENT_IDS.canvas, HTMLCanvasElement);
/** @type {CanvasRenderingContext2D} */
const ctx = canvas.getContext('2d');
/** @type {HTMLImageElement} */
const capturedImage = getEl(ELEMENT_IDS.capturedImage, HTMLImageElement);
/** @type {HTMLElement} */
const loading = getEl(ELEMENT_IDS.loading, HTMLElement);
/** @type {HTMLButtonElement} */
const tryAgainBtn = getEl(ELEMENT_IDS.tryAgainBtn, HTMLButtonElement);
/** @type {HTMLElement} */
const gameInfoDiv = getEl(ELEMENT_IDS.gameInfo, HTMLElement);
/** @type {HTMLElement} */
const gameJsonEl = getEl(ELEMENT_IDS.gameJson, HTMLElement);
/** @type {HTMLElement} */
const warningMsg = getEl(ELEMENT_IDS.warningMsg, HTMLElement);
/** @type {HTMLAudioElement} */
const soundEffect = getEl(ELEMENT_IDS.soundEffect, HTMLAudioElement);

let stream = null;
let pollingInterval = null;
let timeoutTimeMs = 0;
let boundedRect = null;
let boxesQueueLen = 0;
let isSharp = false;

tryAgainBtn.addEventListener('click', resetApp)

/**
 * Initialize the webcam stream and start polling for frames.
 * @returns {Promise<void>}
 */
async function initWebcam() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;

    video.onloadedmetadata = () => {
      show(canvas);
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
 * Capture a frame, send it to the backend, and handle the response.
 * @returns {Promise<void>}
 */
async function captureAndSendFrame() {
  if (!stream || video.videoWidth === 0) return;

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL('image/jpeg');

  try {
    const processedFrame = await apiPost('/process_frame', { image: dataUrl });
    processedFrame.success
      ? await handleSuccessfulDetection(processedFrame)
      : handleUnsuccessfulDetection(processedFrame);
  } catch (err) {
    console.error(err);
    stopWebcam('There has been an error');
  }
}

async function handleSuccessfulDetection(frame) {
  timeoutTimeMs = 0;
  stopWebcam();
  soundEffect.play();

  capturedImage.src = `data:image/jpeg;base64,${frame.image}`;
  show(capturedImage);
  show(loading);
  const gameInfo = await apiPost('/generate_game_info', {
    image: frame.image,
  });
  hide(loading);
  if (gameInfo.success) updateGameInfo(gameInfo);
}

function handleUnsuccessfulDetection(frame) {
  timeoutTimeMs = frame.rect ? 0 : timeoutTimeMs + POLLING_INTERVAL_MS;
  isSharp = frame.is_sharp;
  boxesQueueLen = frame.boxes_queue_len;
  boundedRect = frame.rect;
  if (timeoutTimeMs >= TIMEOUT_LIMIT_MS) {
    stopWebcam('Detection timed out');
  }
}

/**
 * Stop the webcam stream and optionally display a warning message.
 * @param {string=} warningMessage
 * @returns {void}
 */
function stopWebcam(warningMessage) {
  hide(canvas);

  if (pollingInterval) clearInterval(pollingInterval);

  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  if (warningMessage) {
    warningMsg.textContent = warningMessage;
    show(warningMsg);
    show(tryAgainBtn);
  }
}

/**
 * Reset the app UI and state to allow another detection attempt.
 * @returns {void}
 */
function resetApp() {
  hide(capturedImage);
  hide(gameInfoDiv);
  hide(tryAgainBtn);
  hide(loading);
  hide(warningMsg);
  gameJsonEl.textContent = '';
  timeoutTimeMs = 0;
  initWebcam();
}

function updateGameInfo(gameInfo) {
  gameJsonEl.textContent = gameInfoString(gameInfo);
  show(gameInfoDiv);
  show(tryAgainBtn);
}

initWebcam();
