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
let objectedDetected = false;

async function initWebcam() {
  try {
    targetBox.style.display = "none";
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;

    // Match canvas size to video size when metadata is loaded
    video.onloadedmetadata = () => {
      targetBox.style.display = "block";
      canvas.style.display = "block";
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      drawVideoToCanvas();
    };

    pollingInterval = setInterval(captureAndSendFrame, 200);
  } catch (err) {
    alert("Could not access webcam.");
  }
}

// Continuously draw video to canvas for live preview
function drawVideoToCanvas() {
  if (stream && video.videoWidth > 0 && video.videoHeight > 0) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    if (boundedRect) {
      const { x, y, h, w } = boundedRect;
      ctx.beginPath();
      ctx.rect(x, y, h, w);
      ctx.strokeStyle = objectedDetected ? "white" : "blue";
      ctx.stroke();
    }
  }
  requestAnimationFrame(drawVideoToCanvas);
}

async function captureAndSendFrame() {
  if (!stream || video.videoWidth === 0) return;

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg");

  const response = await fetch("/process_frame", {
    method: "POST",
    body: JSON.stringify({ image: dataUrl }),
    headers: { "Content-Type": "application/json" },
  });
  const result = await response.json();

  objectedDetected = result.detected_frames > 0;

  if (result.success) {
    stopWebcam();
    const soundEffect = document.getElementById("soundEffect");
    soundEffect.play();

    canvas.style.display = "none";
    document.getElementById("targetBox").style.display = "none";
    capturedImage.src = result.image_url;
    capturedImage.style.display = "block";
    loading.style.display = "block";

    const filename = result.image_url.split("/").pop();
    const gameInfoRes = await fetch("/process_uploaded_image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });

    const gameInfo = await gameInfoRes.json();
    loading.style.display = "none";

    if (gameInfo.success) {
      const {
        isItAVideoGame,
        title,
        system,
        publisher,
        releaseYear,
        region,
        labelCode,
      } = gameInfo;
      gameJsonEl.textContent = isItAVideoGame
        ? `Title: ${title}\nSystem: ${system}\nPublisher: ${publisher}\nRelease Year: ${releaseYear}\nRegion: ${region}\nLabel Code: ${labelCode}`
        : "Sorry, this is not a video game!";
      gameInfoDiv.style.display = "block";
      tryAgainBtn.style.display = "block";
    }
  } else {
    boundedRect = result.rect;
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
  document.getElementById("targetBox").style.display = "block";
  capturedImage.style.display = "none";
  gameInfoDiv.style.display = "none";
  gameJsonEl.textContent = "";
  loading.style.display = "none";
  initWebcam();
}

  initWebcam();