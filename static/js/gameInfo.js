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