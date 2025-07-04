Prototype video game cartridge label identifier using webcam. Uses flask, cv2 library and open AI API.

The idea is that you can hold a cartridge in front of your webcam, the yolo model will identify the cartridge, an image of the cartridge is then sent to an Open AI model which returns information about the cartridge. It is good on most things, although it struggles with label code and region especially with low-res webcam images.

The underlying yolo model was trained on 300+ images of Game Boy, Game Boy Color, Game Boy Advance, Game Gear, Master Sytem, Mega Drive (including EA, Codemasters and Japanese variants), NES, SNES (not US SNES) and N64 cartridges. It will likely pick up other cartridges, but obviously won't label them correctly (albeit, depending on LLM used, the AI might correctly identity the cartridge after the photo is taken and sent).

Add `config.json` to root of project with

```
{
    "CV2_DEBUG": true,
    "OPENAI_API_KEY": <your key>
}
```

`pip install` requirements and then
`python3 app.py`

Open browser `http://localhost:5001` and give permission to use webcam if asked. Hold a game cartridge up - when the bounding box goes white, hold steady until the webcam takes a picture. If the bounding box is red, it means the image is not sharp enough - keep holding steady, or improve lighting conditions etc. If the bounding box is blue, it means the cartridge needs to fill a bigger percentage of the screen.

CV2_DEBUG, when set to true, logs the AI response to the image.
