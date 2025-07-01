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

async function initWebcam() {    
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      pollingInterval = setInterval(captureAndSendFrame, 200);
    } catch (err) {
      alert('Could not access webcam.');
    }
}

async function captureAndSendFrame() {
    if (!stream || video.videoWidth === 0) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');

    const response = await fetch('/process_frame', {
      method: 'POST',
      body: JSON.stringify({ image: dataUrl }),
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();
    if (result.success) {
      stopWebcam();
      const soundEffect = document.getElementById('soundEffect');
      soundEffect.play()

      video.style.display = 'none';
      document.getElementById('targetBox').style.display = 'none';
      capturedImage.src = result.image_url;
      capturedImage.style.display = 'block';
      loading.style.display = 'block';

      const filename = result.image_url.split('/').pop();
      const gameInfoRes = await fetch('/process_uploaded_image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });

      const gameInfo = await gameInfoRes.json();
      loading.style.display = 'none';

      if (gameInfo.success) {
        gameJsonEl.textContent = `Title: ${gameInfo.title}\nSystem: ${gameInfo.system}\nPublisher: ${gameInfo.publisher}\nRelease Year: ${gameInfo.releaseYear}\nLabel Code: ${gameInfo.labelCode}`;
        gameInfoDiv.style.display = 'block';
        tryAgainBtn.style.display = 'block';
      }
    }
  }

  function stopWebcam() {
    if (pollingInterval) clearInterval(pollingInterval);
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
  }

  function resetApp() {
    video.style.display = 'block';
    document.getElementById('targetBox').style.display = 'block';
    capturedImage.style.display = 'none';
    gameInfoDiv.style.display = 'none';
    gameJsonEl.textContent = '';
    loading.style.display = 'none';
    initWebcam();
  }

  initWebcam();