from pydantic import BaseModel
from typing import Tuple, TypedDict, Literal, NotRequired
from openai import OpenAI
from flask import jsonify, Response
from openai.types.responses import EasyInputMessageParam, ResponseInputImageParam
from openai.types.responses.response_input_item_param import Message


class GameInfoResponseBody(TypedDict):
    success: bool
    error: NotRequired[str]
    reasoning: NotRequired[str | None]
    isItAVideoGame: NotRequired[bool | None]
    title: NotRequired[str | None]
    system: NotRequired[str | None]
    genre: NotRequired[str | None]
    publisher: NotRequired[str | None]
    releaseYear: NotRequired[int | None]
    labelCode: NotRequired[str | None]
    region: NotRequired[str | None]


GameInfoResponseObject = Tuple[Response, Literal[200, 400]]


def generate_game_info(openai_client: OpenAI, image: str, debug: bool) -> GameInfoResponseObject:
    if not image:
        responseBody: GameInfoResponseBody = {
            'success': False, 'error': 'Missing image'}
        return jsonify(responseBody), 400

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

    response = openai_client.responses.parse(
        # model="gpt-4.1",
        model="gpt-4o-mini",
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
            'region': replyDict.get('region')
        }

        if debug:
            print(replyDict.get('reasoning'))
            print(responseBody)
        return jsonify(responseBody), 200
    else:
        return jsonify({"success": False}), 400

#  to do: proper error catching and handling
