# Narrative Video Generator Pipeline

This project introduces an automated pipeline for generating complete, narrated videos. It leverages Large Language Models (LLMs) to brainstorm genres and write scripts, synthesizes voiceovers using Text-to-Speech (TTS), and creates corresponding animated scenes with AI image and video generation. These elements are then seamlessly stitched together into a final video product.

# Features
* AI-Powered Scriptwriting: Automatically generates a script based on the decided genre.
* Automated Narration: Utilizes TTS to create a clear voiceover for the script.
* Dynamic Scene Generation: Creates animated visuals that correspond to the narration using AI.
* End-to-End Automation: Combines the generated audio and visual scenes into a finished video file, ready for viewing.
* Pause and Resume: If the generation process is interrupted, it can be resumed from the last completed step, saving time and computational resources.

# Requirements

* LM Studio
* ComfyUI
* Python 3.10 or higher
* FFMPEG
* LLMs and Image and Video Generation models

Run the following Commands to download the project and install all the python dependencies.

```
git clone https://github.com/Firifire/Narrative-Video-Generator-Pipeline.git
cd Narrative-Video-Generator-Pipeline
pip install -r requirements.txt
```

Ensure all dependencies are installed for workflows in `comfyui_Workflows/`

# Configuration

Edit the `config.py` with the model and voice of choice.

For custom workflows. Edit `generate.py` with the respective node name.

# Usage

To create a new channel idea with a video.
```
python main.py --create
```

To create a new video for an existing channel.
```
python main.py --new "Channel Name"
```

To resume generation for the latest video
```
python main.py --resume "Channel Name"
```

All content generated will be located inside `YT/` folder

