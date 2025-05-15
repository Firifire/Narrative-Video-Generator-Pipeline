import shutil
from pathlib import Path

# Project paths
PROJECT_DIR = Path("my_video_project")
WORKSPACE_DIR = PROJECT_DIR / "workspace"
CONTENT_DIR = PROJECT_DIR / "content"
SCRIPTS_DIR = CONTENT_DIR / "scripts"
STORYBOARD_DIR = CONTENT_DIR / "storyboard"
VIDEO_CLIPS_DIR = CONTENT_DIR / "video_clips"
AUDIO_DIR = CONTENT_DIR / "audio"
NARRATION_DIR = AUDIO_DIR / "narration"
SFX_DIR = AUDIO_DIR / "sfx"
FINAL_VIDEO_DIR = PROJECT_DIR / "final_video"

# LLM Configuration (LM Studio)
LM_STUDIO_SERVER_URL = "http://localhost:1234/v1" # Default LM Studio server
LLM_MODEL_NAME = "gemma-3-4b-it"
LLM_UNLOAD_CMD = ["lms", "unload", LLM_MODEL_NAME]

# ComfyUI Configuration
COMFYUI_BASE_PATH = Path("C:/Application/Apps") # Adjust if your ComfyUI is elsewhere
COMFYUI_INPUT_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "input"
COMFYUI_OUTPUT_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "output"
COMFYUI_MODELS_CHECKPOINTS_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "models" / "checkpoints"
COMFYUI_MODELS_CONTROLNET_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "models" / "controlnet"
COMFYUI_MODELS_UPSCALERS_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "models" / "upscale_models"
COMFYUI_MODELS_VAE_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "models" / "vae"
COMFYUI_MODELS_LORAS_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "models" / "loras"
COMFYUI_MODELS_LTX_VIDEO_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "models" / "checkpoints" # LTX models go here
COMFYUI_MODELS_TEXT_ENCODERS_DIR = COMFYUI_BASE_PATH / "ComfyUI" / "models" / "text_encoders" # For LTX


# Image Generation Parameters
IMAGE_WIDTH = 768
IMAGE_HEIGHT = 512
IMAGE_STEPS = 30
IMAGE_CFG = 7
IMAGE_SAMPLER = "dpmpp_2m_sde_gpu"
IMAGE_SCHEDULER = "karras"
CHARACTER_REFERENCE_IMAGE = None # Path to a character reference image if using one

# Video Generation (LTX-Video via ComfyUI) Parameters
VIDEO_CLIP_FPS = 24
VIDEO_CLIP_MAX_FRAMES = 121 # ~5 seconds at 24fps, LTX-Video sweet spot

# TTS Configuration (Piper TTS assumed for simplicity)
PIPER_EXE_PATH = Path.home() / "piper" / "piper" # Adjust to your Piper TTS executable
PIPER_VOICE_MODEL_PATH = Path.home() / "piper" / "voices" / "en_US-libritts_r-medium.onnx" # Adjust to your downloaded voice
PIPER_VOICE_CONFIG_PATH = str(PIPER_VOICE_MODEL_PATH) + ".json"

# SFX Generation (AudioLDM - command line assumed)
AUDIOLDM_SCRIPT_PATH = "audioldm" # Assuming audioldm is in PATH or provide full path

# Video Assembly Configuration
FINAL_VIDEO_WIDTH = 1280
FINAL_VIDEO_HEIGHT = 720
FINAL_VIDEO_FPS = 24
FFMPEG_PATH = "ffmpeg" # Assuming ffmpeg is in PATH

def setup_directories():
    """Creates necessary project directories."""
    PROJECT_DIR.mkdir(exist_ok=True)
    WORKSPACE_DIR.mkdir(exist_ok=True)
    CONTENT_DIR.mkdir(exist_ok=True)
    SCRIPTS_DIR.mkdir(exist_ok=True)
    STORYBOARD_DIR.mkdir(exist_ok=True)
    VIDEO_CLIPS_DIR.mkdir(exist_ok=True)
    AUDIO_DIR.mkdir(exist_ok=True)
    NARRATION_DIR.mkdir(exist_ok=True)
    SFX_DIR.mkdir(exist_ok=True)
    FINAL_VIDEO_DIR.mkdir(exist_ok=True)
    # ComfyUI input dir might be cleared or managed per run
    if COMFYUI_INPUT_DIR.exists():
        for item in COMFYUI_INPUT_DIR.iterdir():
            if item.is_file():
                item.unlink()
            else:
                shutil.rmtree(item)
    COMFYUI_INPUT_DIR.mkdir(exist_ok=True) # Ensure it exists

def print_stage(title):
    print("\n" + "="*10 + f" {title} " + "="*10)