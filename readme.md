# Retro Game Cartridge Identifier

Prototype video game cartridge label identifier using your webcam. Uses a Flask API backend (YOLO object detection, OpenCV, OpenAI API) and a modern React frontend (Vite). Containerized with Docker Compose for easy development and deployment.

## Project Overview

Hold a cartridge in front of your webcam—the YOLO model will detect the cartridge, take a snapshot, and send it to the OpenAI API to retrieve information about the game. The system is trained on 300+ images of Game Boy, Game Boy Color, Game Boy Advance, Game Gear, Master System, Mega Drive (including EA, Codemasters, Japanese variants), NES, SNES (not US SNES), and N64 cartridges. It may detect other cartridges, but labeling accuracy may vary.

- **Backend:** Python Flask API (YOLOv4-tiny, OpenCV, OpenAI API)
- **Frontend:** React (Vite, modular components, webcam integration)
- **Containerization:** Docker Compose (multi-service orchestration)

## Features
- Real-time webcam detection of retro game cartridges
- YOLO-based object detection for bounding box and cropping
- Sends cropped image to OpenAI API for game info
- UI feedback: bounding box color (white = sharp, red = blurry, blue = too small)
- Timeout and error handling, "Try Again" workflow

## Architecture

```
[User Webcam]
     │
[React Frontend (Vite)]
     │   (API calls, UI, webcam)
     ▼
[Flask API Backend]
     │   (YOLO detection, OpenCV, OpenAI)
     ▼
[OpenAI API]
```

- **Frontend:** Runs on http://localhost:3000 (dev) or http://localhost:3000 (prod via Nginx)
- **Backend:** Runs on http://localhost:5001 (API only)

## Quick Start

### 1. Prerequisites
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed
- OpenAI API key

### 2. Create a `.env` file in your project root:
```
OPENAI_API_KEY=your_actual_key_here
```

### 3. Development: Hot Reload with Docker Compose

- Use `docker compose.dev.yml` for development (hot reload, code mounting).
- The backend uses `watchmedo auto-restart` for robust hot reload with native libraries (OpenCV, numpy, etc.).
- **Recommended:** Use the provided shortcut script:

```sh
./dev.sh up --build
```
- This runs Docker Compose in development mode with hot reload for both backend and frontend.
- You can pass any arguments to Docker Compose through this script (e.g., `./dev.sh down`).

- **Alternatively,** you can run Docker Compose directly:

```sh
docker compose -f docker compose.dev.yml up --build
```
- The Flask API will be available at http://localhost:5001 (auto-reloads on code changes)
- The frontend will be available at http://localhost:3000 (auto-reloads on code changes)

### 4. Production: Optimized Builds

- Use `docker compose.yml` for production (optimized, no code mounting, static serving).
- **To build and run for production:**

```sh
docker compose up --build
```
- The frontend will be served by Nginx at http://localhost:3000
- The backend will be at http://localhost:5001

### 5. Stopping
```sh
docker compose down
```

### 6. Rebuilding (if you change dependencies):
```sh
docker compose build
```

## Development Workflow
- Edit backend code in `api-flask/` and frontend code in `frontend/`.
- Hot reload is enabled in development by default.
- For production, use the optimized Dockerfiles and do not mount code as volumes.
- You can run the frontend and backend separately for local development if desired.

## Usage
1. Open http://localhost:3000 in your browser.
2. Allow webcam access when prompted.
3. Hold a game cartridge up to the webcam.
   - **White bounding box:** Hold steady, image is sharp, snapshot will be taken.
   - **Red bounding box:** Image is blurry, hold steady or improve lighting.
   - **Blue bounding box:** Cartridge needs to fill more of the screen.
4. After a snapshot, game info will be displayed (if recognized).
5. If detection times out or fails, use the "Try Again" button.

## Tech Stack
- **Backend:** Python 3.13, Flask, OpenCV, YOLOv4-tiny, OpenAI API
- **Frontend:** React 19, Vite, modern hooks/components
- **Containerization:** Docker, Docker Compose, Nginx (for production frontend)

## YOLO Model Training
The YOLO model was trained on a custom dataset of retro cartridges. For details on training your own YOLO models, see: https://github.com/moises-dias/yolo-opencv-detector

## Troubleshooting
- If you see errors about missing libraries (e.g., `libGL.so.1`), ensure Docker images are rebuilt.
- For CORS issues, always access the frontend via http://localhost:3000 (not file:// URLs).
- If the backend is flaky, restart the containers with `docker compose down && docker compose up --build`.

## License
This is a prototype for educational and demonstration purposes only.
