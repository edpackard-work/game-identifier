const video = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const capturedImage = document.getElementById('capturedImage');
const loading = document.getElementById('loading');
const tryAgainBtn = document.getElementById('tryAgainBtn');
const gameInfoDiv = document.getElementById('gameInfo');
const gameJsonEl = document.getElementById('gameJson');

let stream = null;
let pollingInterval = null;
let boundedRect = null;
let boxesQueueLen = 0;
let isSharp = false;
let objectedDetected = false;

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

    pollingInterval = setInterval(captureAndSendFrame, 200);
  } catch (err) {
    alert('Could not access webcam.');
  }
}

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

async function captureAndSendFrame() {
  if (!stream || video.videoWidth === 0) return;

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL('image/jpeg');

  let result;

  try {
    const response = await fetch('/process_frame', {
      method: 'POST',
      body: JSON.stringify({ image: dataUrl }),
      headers: { 'Content-Type': 'application/json' },
    });
    result = await response.json();

    if (result.success) {
      stopWebcam();
      const soundEffect = document.getElementById('soundEffect');
      soundEffect.play();

      canvas.style.display = 'none';
      capturedImage.src = `data:image/jpeg;base64,${result.image}`;
      capturedImage.style.display = 'block';
      loading.style.display = 'block';

      const gameInfoRes = await fetch('/generate_game_info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: result.image }),
      });

      const gameInfo = await gameInfoRes.json();
      loading.style.display = 'none';

      if (gameInfo.success) {
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
    } else {
      isSharp = result.is_sharp;
      boxesQueueLen = result.boxes_queue_len;
      boundedRect = result.rect;
    }
  } catch (err) {
    console.log(err);
    stopWebcam();
    canvas.style.display = 'none';
    tryAgainBtn.style.display = 'block';
  }
}

function stopWebcam() {
  if (pollingInterval) clearInterval(pollingInterval);
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }
}

function resetApp() {
  capturedImage.style.display = 'none';
  gameInfoDiv.style.display = 'none';
  tryAgainBtn.style.display = 'none';
  gameJsonEl.textContent = '';
  loading.style.display = 'none';
  initWebcam();
}

initWebcam();
