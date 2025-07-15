export const ELEMENT_IDS = {
  video: 'webcam',
  canvas: 'canvas',
  capturedImage: 'capturedImage',
  loading: 'loading',
  tryAgainBtn: 'tryAgainBtn',
  gameInfo: 'gameInfo',
  gameJson: 'gameJson',
  warningMsg: 'warningMsg',
  soundEffect: 'soundEffect',
};

/**
 * @template {HTMLElement} T
 * @param {string} id
 * @param {new () => T} type
 * @returns {T}
 */
export function getEl(id, type) {
  const el = document.getElementById(id);
  if (!el || !(el instanceof type)) {
    throw new Error(`Missing or invalid element for ID: ${id}`);
  }
  return el;
}

export function show(el) {
  el.style.display = 'block';
}

export function hide(el) {
  el.style.display = 'none';
}