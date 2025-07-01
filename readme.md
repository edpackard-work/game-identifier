Prototype video game cartridge label identifier using webcam. Uses flask, cv2 library and open AI API.

Add `config.json` to root of project with 

```
{
    "CV2_DEBUG": true,
    "OPENAI_API_KEY": <your key>
}
```

`pip install` requirements and then 
python3 app.py

Open browser `http://localhost:5000` and give permission to use webcam if asked. Hold a game cartridge up in the green square until captured - rectangular grey cartridges (Game Boy, NES, SNES for example) work best.

CV2_DEBUG, when set to true, displays a blue bounding box on the frontend to show what object is being tracked, and also saves more information on the backend in the `captured` directory.