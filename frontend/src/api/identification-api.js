
const API_BASE_URL = 'http://localhost:5001';

/**
 * @typedef {Object} Rect
 * @property {number} x
 * @property {number} y
 * @property {number} w
 * @property {number} h
 * @property {string} label
 * @property {number} confidence
 */

/**
 * @typedef {Object} PostProcessResponseBody
 * @property {boolean} success
 * @property {string} [image]
 * @property {Rect} [rect]
 * @property {boolean} [is_sharp]
 * @property {number} [boxes_queue_len]
 */

/**
 * @typedef {Object} GameInfoResponseBody
 * @property {boolean} success
 * @property {string} [error]
 * @property {boolean} [isItAVideoGame]
 * @property {string} [title]
 * @property {string} [system]
 * @property {string} [genre]
 * @property {string} [publisher]
 * @property {number} [releaseYear]
 * @property {string} [labelCode]
 * @property {string} [region]
 */ 

/**
 * Helper to POST image data to a backend API route.
 * @param {string} route - The API route (e.g., '/process_frame').
 * @param {string} errorMessage - Error message to throw if the request fails.
 * @param {string} imageData - The image data to send.
 * @returns {Promise<Object>} The parsed JSON response from the backend.
 * @throws {Error} If the response is not ok.
 */
async function postImageToApi(route, errorMessage, imageData) {
  const response = await fetch(`${API_BASE_URL}${route}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageData }),
  });
  if (!response.ok) {
    throw new Error(errorMessage);
  }
  return response.json();
}

/**
 * Sends a frame image to the backend for YOLO detection.
 * @param {string} imageDataUrl - The image data from the canvas.
 * @returns {Promise<PostProcessResponseBody>} The YOLO detection result from the backend.
 */
export function processFrame(imageDataUrl) {
  return postImageToApi('/process_frame', 'Failed to process frame', imageDataUrl);
}

/**
 * Requests game information from the backend using a detected image.
 * @param {string} imageBase64 - The base64-encoded image string.
 * @returns {Promise<GameInfoResponseBody>} The game info result from the backend.
 */
export function generateGameInfo(imageBase64) {
  return postImageToApi('/generate_game_info', 'Failed to fetch game info', imageBase64);
} 