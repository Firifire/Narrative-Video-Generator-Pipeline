import shutil
from pathlib import Path
from utils import *

##################################################################
# ===================== PATH CONFIGURATION ===================== #
##################################################################

# LLM Configuration (LM Studio)
LM_STUDIO_SERVER_URL = "http://localhost:1234/v1" # Default LM Studio server
LLM_MODEL_NAME = "gemma-3-12b-it-qat"
LLM_UNLOAD_CMD = ["lms", "unload", LLM_MODEL_NAME]

# ComfyUI Configuration
COMFYUI_SERVER_URL = "127.0.0.1:8000"

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


FFMPEG_PATH = "ffmpeg" # Assuming ffmpeg is in PATH


###################################################################
# ===================== AUDIO CONFIGURATION ===================== #
###################################################################

# Using Kokoro TTS for narration
KOKORO_LANG = "a"
KOKORO_VOICE_NAME = "af_jessica"

###################################################################
# ===================== IAMGE CONFIGURATION ===================== #
###################################################################

# ComfyUI Workflow
TXT2IMG_WORKFLOW = Path("comfyui_workflows/yt_txt3img.json") # Path to your ComfyUI text-to-image workflow

# Image Generation Parameters
IMAGE_WIDTH = 768
IMAGE_HEIGHT = 512
IMAGE_STEPS = 30
IMAGE_CFG = 7
IMAGE_SAMPLER = "dpmpp_2m_sde_gpu"
IMAGE_SCHEDULER = "karras"

###################################################################
# ===================== VIDEO CONFIGURATION ===================== #
###################################################################

# ComfyUI Workflow
IMG2VID_WORKFLOW = Path("comfyui_workflows/ltx_img2vid_api.json") # Path to your ComfyUI image-to-video workflow

# Image Generation Parameters
IMAGE_WIDTH = 768
IMAGE_HEIGHT = 512
IMAGE_STEPS = 30
IMAGE_CFG = 7
IMAGE_SAMPLER = "dpmpp_2m_sde_gpu"
IMAGE_SCHEDULER = "karras"

# Video Generation (LTX-Video via ComfyUI) Parameters
VIDEO_CLIP_FPS = 24
VIDEO_CLIP_MAX_FRAMES = 121 # ~5 seconds at 24fps, LTX-Video sweet spot

# TTS Configuration (Piper TTS assumed for simplicity)
PIPER_EXE_PATH = Path.home() / "piper" / "piper" # Adjust to your Piper TTS executable
PIPER_VOICE_MODEL_PATH = Path.home() / "piper" / "voices" / "en_US-libritts_r-medium.onnx" # Adjust to your downloaded voice
PIPER_VOICE_CONFIG_PATH = str(PIPER_VOICE_MODEL_PATH) + ".json"

# Video Assembly Configuration
FINAL_VIDEO_WIDTH = 1280
FINAL_VIDEO_HEIGHT = 720
FINAL_VIDEO_FPS = 24