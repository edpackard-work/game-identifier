from pydantic import BaseModel
from typing import TypedDict, NotRequired
from openai import OpenAI
from openai.types.responses import EasyInputMessageParam, ResponseInputImageParam
from openai.types.responses.response_input_item_param import Message
import logging


class GameInfoResponseBody(TypedDict):
    success: bool
    error: NotRequired[str | None]
    isItAVideoGame: NotRequired[bool | None]
    title: NotRequired[str | None]
    system: NotRequired[str | None]
    genre: NotRequired[str | None]
    publisher: NotRequired[str | None]
    releaseYear: NotRequired[int | None]
    labelCode: NotRequired[str | None]
    region: NotRequired[str | None]


def generate_game_info(openai_client: OpenAI, image: str, debug: bool) -> GameInfoResponseBody:
    logging.debug("generate_game_info called with image: %s", 'provided' if image else 'missing')
    if not image:
        logging.error("No image provided to generate_game_info")
        return {'success': False, 'error': 'Missing image'}

    class GameDetails(BaseModel):
        reasoning: str
        isItAVideoGame: bool | None = None
        title: str | None = None
        system: str | None = None
        genre: str | None = None
        publisher: str | None = None
        releaseYear: int | None = None
        labelCode: str | None = None
        region: str | None = None

    system_message: EasyInputMessageParam = {"role": "system", "content": "You are an expert video game identifier. \
             Consider the game cartridge type and label text, \
             alongside your knowledge to identify the game in the image provided. \
             isItAVideoGame: if this is false, return '' for title, system, publisher, releaseYear and labelCode. \
             title: the game's title. \
             system: do not include manufacturer (i.e. return Game Boy not Nintendo Game Boy, or return Mega Drive not Sega Mega Drive) \
             genre: a one or two word summary of the game's primary genre (i.e. Puzzle, Platformer, Action-Adventure, RPG etc) \
             publisher: the game's publisher on this particular system, usually but not always displayed on the label text \
             releaseYear: the game's release year on this particular system and region \
             labelCode: the game's label code (if present) in the acknowledged system format (i.e. a DMG code for Game Boy) \
             region: based on cartridge type, artwork and label, return the region (i.e. Europe, United Kingdom, Japan, United States etc) \
             Return '' if you are not sure about any field."}
    input_image: ResponseInputImageParam = {
        "type": "input_image", "image_url": f"data:image/jpeg;base64,{image}", "detail": "auto"}
    user_message: Message = {"role": "user", "content": [input_image]}

    try:
        response = openai_client.responses.parse(
            model="gpt-4.1",
            # model="gpt-4o-mini",
            temperature=0,
            input=[system_message, user_message],
            text_format=GameDetails,
        )
        reply: GameDetails | None = response.output_parsed
        if reply:
            replyDict = reply.model_dump()
            responseBody: GameInfoResponseBody = {
                'success': True,
                'isItAVideoGame': replyDict.get('isItAVideoGame'),
                'title': replyDict.get('title'),
                'system': replyDict.get('system'),
                'genre': replyDict.get('genre'),
                'publisher': replyDict.get('publisher'),
                'releaseYear': replyDict.get('releaseYear'),
                'labelCode': replyDict.get('labelCode'),
                'region': replyDict.get('region'),
                'error': None,
            }
            if debug:
                logging.debug("OpenAI reasoning: %s", replyDict.get('reasoning'))
                logging.debug("Game info response: %s", responseBody)
            return responseBody
        else:
            logging.error("No reply from OpenAI API")
            return {"success": False, 'error': 'No reply from OpenAI API'}
    except Exception as e:
        logging.exception("Exception in generate_game_info")
        return {"success": False, 'error': str(e)}
