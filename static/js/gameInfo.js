/**
 * Format game info object as a display string.
 * @param {object} params
 * @param {boolean} params.isItAVideoGame
 * @param {string} params.title
 * @param {string} params.system
 * @param {string} params.genre
 * @param {string} params.publisher
 * @param {number|string} params.releaseYear
 * @param {string} params.region
 * @param {string} params.labelCode
 * @returns {string}
 */
export function gameInfoString({
  isItAVideoGame,
  title,
  system,
  genre,
  publisher,
  releaseYear,
  region,
  labelCode,
}) {
  if (!isItAVideoGame) {
    return 'Sorry, this is not a video game!';
  }

  return [
    `Title: ${title}`,
    `System: ${system}`,
    `Genre: ${genre}`,
    `Publisher: ${publisher}`,
    `Release Year: ${releaseYear}`,
    `Region: ${region}`,
    `Label Code: ${labelCode}`,
  ].join('\n');
}
