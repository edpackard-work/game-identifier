/**
 * Send a POST request to the given route.
 * @param {string} route
 * @param {object} body
 * @returns {Promise<any>} The parsed JSON response
 */
export async function apiPost(route, body) {
  const response = await fetch(route, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
}