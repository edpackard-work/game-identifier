from pydantic import BaseModel

def generate_game_info(openai_client, image, config):
    if not image:
        return {'success': False, 'error': 'Missing image'}, 400
    
    class GameDetails(BaseModel):
        reasoning: str
        isItAVideoGame: bool
        title: str | None=None
        system: str | None=None
        genre: str | None=None
        publisher: str | None=None
        releaseYear: int | None=None
        labelCode: str | None=None
        region: str | None=None
    
    response = openai_client.responses.parse(
        # model="gpt-4.1",
        model="gpt-4o-mini",
        temperature=0,
        input=[
            {"role": "system", "content": "You are an expert video game identifier. \
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
             Return '' if you are not sure about any field."},
            {"role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{image}"}
                ]
            }
        ],
        text_format=GameDetails,
    )
    success = {'success': True}
    reply = response.output_parsed
    responseJson = {**success, **reply.model_dump(mode='json')}
    if config.get("CV2_DEBUG") == True:
        print(responseJson)
    return responseJson 