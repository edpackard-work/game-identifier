Prototype video game cartridge label identifier using webcam. Uses flask, a lightweight yolo model, cv2 library and open AI API.

Currently implementing a React frontend and docker containers for front and back ends - see branch here: https://github.com/edpackard-work/game-identifier/tree/implement-react-frontend

For venv set up, Python version 3.13 recommended.

The idea is that you can hold a cartridge in front of your webcam, the yolo model will identify the cartridge, an image of the cartridge is then sent to an Open AI model which returns information about the cartridge. It is good on most things, although it struggles with label code and region especially with low-res webcam images.

The underlying yolo model was trained on 300+ images of Game Boy, Game Boy Color, Game Boy Advance, Game Gear, Master Sytem, Mega Drive (including EA, Codemasters and Japanese variants), NES, SNES (not US SNES) and N64 cartridges. It will likely pick up other cartridges, but obviously won't label them correctly (albeit, depending on LLM used, the AI might correctly identity the cartridge after the photo is taken and sent).

This is a really good tutorial for training yolo models: https://github.com/moises-dias/yolo-opencv-detector

## Get started

Either:

Set an env var `OPENAI_API_KEY=your_actual_key_here`

`pip install` requirements and then
`python3 app.py`

Or follow the docker instructions below. 

Once up and running open browser `http://localhost:5001` and give permission to use webcam if asked. Hold a game cartridge up - when the bounding box goes white, hold steady until the webcam takes a picture. If the bounding box is red, it means the image is not sharp enough - keep holding steady, or improve lighting conditions etc. If the bounding box is blue, it means the cartridge needs to fill a bigger percentage of the screen.

## Docker Compose Development Workflow

### 1. Create a `.env` file in your project root:
```
OPENAI_API_KEY=your_actual_key_here
```

### 2. Start the app with Docker Compose:
```sh
docker-compose up
```

- The app will be available at http://localhost:5001
- Any code changes will be reflected automatically (if `debug=True` in your app).
- To stop, press Ctrl+C or run `docker-compose down`.

### 3. Rebuilding (if you change dependencies):
```sh
docker-compose build
```

---
