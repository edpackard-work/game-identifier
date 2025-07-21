/**
 * @param {Object} props
 * @param {import('./api/identification-api').GameInfoResponseBody} props.gameInfo
 */
function GameInfoDisplay({ gameInfo }) {
  if (!gameInfo || gameInfo.isItAVideoGame === false) {
    return <div>Sorry, this is not a video game!</div>;
  }
  return (
    <pre>
      {[
        `Title: ${gameInfo.title || ''}`,
        `System: ${gameInfo.system || ''}`,
        `Genre: ${gameInfo.genre || ''}`,
        `Publisher: ${gameInfo.publisher || ''}`,
        `Release Year: ${gameInfo.releaseYear || ''}`,
        `Region: ${gameInfo.region || ''}`,
        `Label Code: ${gameInfo.labelCode || ''}`,
      ].join('\n')}
    </pre>
  );
}

export default GameInfoDisplay; 