import os
import json
import subprocess
import shutil
from pathlib import Path

# --- Configuration - User needs to set these paths and parameters ---

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

# LLM Configuration (LM Studio assumed)
LM_STUDIO_SERVER_URL = "http://localhost:1234/v1" # Default LM Studio server
LLM_MODEL_NAME = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF" # Replace with your downloaded model
# Or for Llama 3: LLM_MODEL_NAME = "SanctumAI/Meta-Llama-3-8B-Instruct-GGUF"

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

# --- Helper Functions ---

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

def llm_generate(prompt, system_prompt="You are a helpful AI assistant.", temperature=0.7, max_tokens=2048):
    """Generates text using the LLM via LM Studio's API."""
    import requests # Local import to keep main script cleaner if LM Studio not used directly
    payload = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    try:
        response = requests.post(f"{LM_STUDIO_SERVER_URL}/chat/completions", json=payload, timeout=300)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"LLM generation failed: {e}")
        return None

def generate_comfyui_image(workflow_api_json_path, input_prompts, output_prefix, iteration):
    """
    Triggers a ComfyUI workflow to generate an image.
    Assumes workflow_api_json_path is a ComfyUI API format JSON.
    Input_prompts is a dictionary to update specific nodes in the workflow.
    """
    import requests
    import uuid
    import websocket
    import urllib.parse
    import time

    server_address = "127.0.0.1:8000" # Default ComfyUI server
    client_id = str(uuid.uuid4())

    try:
        with open(workflow_api_json_path, 'r') as f:
            prompt_workflow = json.load(f)

        # Modify the workflow with new prompts
        # This is highly dependent on your specific ComfyUI workflow structure
        # Example: Assuming you have nodes with titles like "Positive Prompt" and "Negative Prompt"
        # And potentially a "Load Image" node for ControlNet reference
        for node_id, node_data in prompt_workflow.items():
            if node_data.get("_meta", {}).get("title") == "Positive Prompt":
                prompt_workflow[node_id]["inputs"]["text"] = input_prompts.get("positive_prompt", "")
            if node_data.get("_meta", {}).get("title") == "Negative Prompt":
                prompt_workflow[node_id]["inputs"]["text"] = input_prompts.get("negative_prompt", "ugly, bad anatomy")
            if node_data.get("_meta", {}).get("title") == "Empty Latent Image": # Common for image size
                 prompt_workflow[node_id]["inputs"]["width"] = IMAGE_WIDTH
                 prompt_workflow[node_id]["inputs"]["height"] = IMAGE_HEIGHT
            if node_data.get("_meta", {}).get("title") == "KSampler": # Common for sampler settings
                prompt_workflow[node_id]["inputs"]["steps"] = IMAGE_STEPS
                prompt_workflow[node_id]["inputs"]["cfg"] = IMAGE_CFG
                prompt_workflow[node_id]["inputs"]["sampler_name"] = IMAGE_SAMPLER
                prompt_workflow[node_id]["inputs"]["scheduler"] = IMAGE_SCHEDULER
                prompt_workflow[node_id]["inputs"]["seed"] = input_prompts.get("seed", 12345) # Use a consistent seed for consistency
            # Add more modifications for ControlNet nodes if used (e.g., loading reference image)

        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}")

        payload = {"prompt": prompt_workflow, "client_id": client_id}
        ws.send(json.dumps(payload))

        print(f"Sent image generation request to ComfyUI for {output_prefix}_{iteration}")

        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == payload['prompt_id']:
                        break #Execution is done
                elif message['type'] == 'executed' and message['data']['node_id'] in prompt_workflow: # Assuming last node is save/preview
                    # This part is tricky as it depends on how your workflow outputs images
                    # We'll assume images are saved in ComfyUI's output directory
                    # and try to find the latest one. A more robust way is to have a specific "SaveImage" node
                    # and get its output filename from the 'executed' message.
                    time.sleep(2) # Give time for file to be written
                    break
            else:
                # Binary message, potentially image data if your workflow sends it via websocket.
                # For simplicity, we'll rely on finding it in the output folder.
                pass
        ws.close()

        # Find the generated image (this is a heuristic)
        # A better way is to use a "Save Image" node in ComfyUI that provides the filename.
        # Or use the ComfyUI API to fetch the image if the workflow returns it directly.
        generated_files = sorted(COMFYUI_OUTPUT_DIR.glob(f"ComfyUI_*.png"), key=os.path.getmtime, reverse=True)
        if generated_files:
            latest_file = generated_files[0]
            output_path = STORYBOARD_DIR / f"{output_prefix}_{iteration}.png"
            shutil.copy(latest_file, output_path)
            print(f"Image saved to {output_path}")
            return str(output_path)
        else:
            print(f"Could not find generated image for {output_prefix}_{iteration} in {COMFYUI_OUTPUT_DIR}")
            return None

    except Exception as e:
        print(f"ComfyUI image generation failed for {output_prefix}_{iteration}: {e}")
        return None


def generate_comfyui_video_clip(workflow_api_json_path, image_paths, output_video_name, scene_index, clip_index):
    """
    Triggers a ComfyUI LTX-Video workflow.
    Assumes workflow_api_json_path points to an LTX-Video API workflow.
    image_paths is a list of paths to storyboard frames for the clip.
    """
    import requests
    import uuid
    import websocket
    import urllib.parse
    import time

    server_address = "127.0.0.1:8000"
    client_id = str(uuid.uuid4())

    try:
        with open(workflow_api_json_path, 'r') as f:
            prompt_workflow = json.load(f)

        # --- Modify LTX-Video workflow ---
        # This is HIGHLY dependent on your LTX-Video workflow structure in ComfyUI.
        # You'll need to identify the node IDs for:
        # 1. Loading the initial image (if image-to-video)
        # 2. Setting the text prompt (if text-to-video or to guide image-to-video)
        # 3. Setting number of frames, FPS
        # 4. Save video node (to get the output filename)

        # Example: Assuming first image is the main input
        first_frame_path_comfy = str(Path(COMFYUI_INPUT_DIR) / Path(image_paths[0]).name)
        shutil.copy(image_paths[0], first_frame_path_comfy) # Copy to ComfyUI input

        for node_id, node_data in prompt_workflow.items():
            if node_data.get("_meta", {}).get("title") == "Load Image": # Placeholder title
                prompt_workflow[node_id]["inputs"]["image"] = Path(image_paths[0]).name
            if node_data.get("_meta", {}).get("title") == "CLIP Text Encode (Positive Prompt)": # Placeholder title
                # You might get this from the scene_data or a generic prompt
                prompt_workflow[node_id]["inputs"]["text"] = f"Animated scene based on the input image. Scene {scene_index}, Clip {clip_index}"
            if node_data.get("_meta", {}).get("title") == "🅛🅣🅧 LTXV Base Sampler": # Placeholder title
                prompt_workflow[node_id]["inputs"]["num_frames"] = VIDEO_CLIP_MAX_FRAMES
                # prompt_workflow[node_id]["inputs"]["fps"] = VIDEO_CLIP_FPS
            # For workflows using multiple guiding images (first, middle, last):
            # You would copy these to COMFYUI_INPUT_DIR and update respective "Load Image" nodes.

        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
        payload = {"prompt": prompt_workflow, "client_id": client_id}
        ws.send(json.dumps(payload))
        print(f"Sent LTX-Video generation request to ComfyUI for {output_video_name}")

        output_filename = None
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executed':
                    # Check for output from a "Save Video" or "Video Combine" node
                    # This assumes the node's output data contains filename info.
                    # Example: if message['data']['output'].get('videos'):
                    # output_filename = message['data']['output']['videos'][0]['filename']
                    # break
                    # For now, we rely on finding the latest video in output dir as a fallback
                    if message['data']['node_id'] in prompt_workflow: # A heuristic, find your save node ID
                        time.sleep(5) # Give more time for video saving
                        break
                elif message['type'] == 'executing' and message['data']['node'] is None:
                    break # Execution finished
            else:
                pass # Binary data
        ws.close()

        # Find the generated video (heuristic)
        generated_files = sorted(COMFYUI_OUTPUT_DIR.glob(f"*.mp4"), key=os.path.getmtime, reverse=True) # Adjust extension if different
        if generated_files:
            latest_file = generated_files[0]
            output_path = VIDEO_CLIPS_DIR / output_video_name
            shutil.copy(latest_file, output_path)
            # Clean up the ComfyUI output dir to avoid picking the same file next time
            # latest_file.unlink() # Be careful with this in a real setup
            print(f"Video clip saved to {output_path}")
            return str(output_path)
        else:
            print(f"Could not find generated video {output_video_name} in {COMFYUI_OUTPUT_DIR}")
            return None

    except Exception as e:
        print(f"ComfyUI LTX-Video generation failed for {output_video_name}: {e}")
        return None

def generate_tts_audio(text, output_filename):
    """Generates audio from text using Piper TTS."""
    output_path = NARRATION_DIR / output_filename
    command = [
        str(PIPER_EXE_PATH),
        "--model", str(PIPER_VOICE_MODEL_PATH),
        "--config", str(PIPER_VOICE_CONFIG_PATH),
        "--output_file", str(output_path)
    ]
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=text.encode('utf-8'))
        if process.returncode != 0:
            print(f"Piper TTS error: {stderr.decode()}")
            return None
        print(f"Narration audio saved to {output_path}")
        return str(output_path)
    except Exception as e:
        print(f"Piper TTS failed: {e}")
        return None

def generate_sfx_audio(prompt, output_filename):
    """Generates SFX using AudioLDM."""
    output_path = SFX_DIR / output_filename
    # Example: audioldm -t "footsteps on gravel" --duration 3 --save_path ./sfx_output/
    # You'll need to parse the output to find the actual filename if it's not exact.
    # This is a simplified version.
    command = [
        AUDIOLDM_SCRIPT_PATH,
        "-t", prompt,
        "--duration", "3", # Default duration
        "--save_path", str(SFX_DIR), # AudioLDM might create subdirs
        # Potentially add a naming convention or parse its output to get the exact file.
        # For simplicity, we assume it saves as output_filename directly or we find it.
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        # This is a placeholder - AudioLDM might save with a different name or in a subfolder.
        # You'd need a more robust way to locate the specific SFX file.
        # For this script, we'll assume it creates output_filename or we manually place it.
        if output_path.exists(): # Check if the file was created as expected
             print(f"SFX audio saved/found at {output_path} (verify filename from AudioLDM output)")
             return str(output_path)
        else: # Try finding a recently created file if naming is dynamic
            sfx_files = sorted(SFX_DIR.glob(f"*{prompt.replace(' ','_')}*.wav"), key=os.path.getmtime, reverse=True)
            if sfx_files:
                shutil.move(sfx_files[0], output_path)
                print(f"SFX audio (renamed) saved to {output_path}")
                return str(output_path)
            print(f"SFX generation for '{prompt}' seemed to run, but output file {output_path} not found directly. Check {SFX_DIR}.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"AudioLDM SFX generation failed for '{prompt}': {e.stderr}")
        return None
    except Exception as e:
        print(f"AudioLDM SFX generation failed: {e}")
        return None


def get_word_timestamps_from_audio(narration_audio_path, narration_text):
    """Uses Whisper (via stable-ts) to get word-level timestamps."""
    try:
        import stable_whisper
        model = stable_whisper.load_model('base') # Or other sizes like 'small', 'medium'
        result = model.align(narration_audio_path, narration_text, language='en') # Assuming English
        
        timestamps = []
        for segment in result.segments:
            for word_info in segment.words:
                timestamps.append({
                    "word": word_info.word,
                    "start": word_info.start,
                    "end": word_info.end
                })
        print(f"Generated timestamps for {Path(narration_audio_path).name}")
        return timestamps
    except ImportError:
        print("stable-ts library not found. Please install it: pip install -U stable-ts")
        return []
    except Exception as e:
        print(f"Timestamp generation failed for {Path(narration_audio_path).name}: {e}")
        return []

def assemble_final_video(video_clips_paths, narration_segments, sfx_items, output_video_path):
    """Assembles the final video using FFmpeg."""
    if not video_clips_paths:
        print("No video clips provided for assembly.")
        return

    # Create a file list for FFmpeg concat demuxer
    concat_file_list = WORKSPACE_DIR / "ffmpeg_concat_list.txt"
    with open(concat_file_list, "w") as f:
        for clip_path in video_clips_paths:
            f.write(f"file '{Path(clip_path).resolve()}'\n")

    inputs = [f"-f", "concat", "-safe", "0", "-i", str(concat_file_list)]
    audio_maps = []
    filter_complex_parts = []
    
    current_video_duration = 0
    video_durations = []
    for i, clip_path in enumerate(video_clips_paths):
        try:
            result = subprocess.run([FFMPEG_PATH, '-i', str(Path(clip_path).resolve()), '-hide_banner'], capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            # FFmpeg outputs duration info to stderr
            duration_line = [line for line in e.stderr.split('\n') if "Duration:" in line]
            if duration_line:
                parts = duration_line[0].split(",")[0].split("Duration: ")[1].split(":")
                duration = int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
                video_durations.append(duration)
            else:
                print(f"Warning: Could not get duration for {clip_path}. Assuming 0.")
                video_durations.append(0) # Default or handle error
        else: # Should not happen if only duration is needed, but good for general check
             print(f"Warning: Could not get duration for {clip_path} via error parsing. Assuming 0.")
             video_durations.append(0)


    # Narration
    narration_offset = 0
    for i, segment in enumerate(narration_segments):
        audio_path = segment["audio_path"]
        start_time = segment["start_time"] # Absolute start time in the final video
        inputs.extend(["-i", str(Path(audio_path).resolve())])
        audio_stream_index = len(video_clips_paths) + i # base inputs + previous narrations
        
        # We need to map this audio to start at `start_time`
        # For simplicity, we'll map all narration to one track and handle offsets later if needed,
        # or assume TTS generates segments that are stitched together sequentially by FFmpeg.
        # A more robust way is to create silent audio of correct length and overlay.
        # Here, we assume narration audio files are for sequential parts of the script.
        # We'll use amix or complex filter graph later. For now, just add as inputs.
        # This example assumes a single continuous narration track made of segments.
        # If segments are separate and timed, a complex filter_complex is needed.

        # Simplified: Assume narration_audio_path is one continuous track for now.
        # This part needs significant improvement if narration is segmented and timed.
        # For now, we'll map the first narration track if it exists.
        if i == 0 and audio_path: # Placeholder for a single main narration track
            audio_maps.append(f"-map {len(inputs)-2}:a") # Map the last added audio input

    # SFX
    sfx_input_count = 0
    for i, sfx in enumerate(sfx_items):
        audio_path = sfx["audio_path"]
        start_time = sfx["start_time"] # Absolute start time
        sfx_input_index = len(inputs) # Current count before adding this SFX
        inputs.extend(["-i", str(Path(audio_path).resolve())])
        
        # Example of delaying SFX: [sfx_input_index:a]adelay=START_MS[sfx_delayed_i];
        # Then mix [sfx_delayed_i] with main audio.
        # This gets very complex quickly with many SFX.
        # For now, just adding them as inputs, manual mixing/timing in FFmpeg is hard this way.
        # A better approach: create a single mixed audio track first, then add to video.
        # Or use a complex filter_complex.
        # This part is a placeholder for a more robust SFX mixing strategy.
        if audio_path: # Map first SFX for now
             if not audio_maps: # If no narration, SFX is first audio
                  audio_maps.append(f"-map {sfx_input_index}:a")
             sfx_input_count +=1


    command = [FFMPEG_PATH] + inputs
    command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])
    
    if audio_maps: # If we have any audio to map
        command.extend(audio_maps)
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    else: # No audio, just copy video
        command.extend(["-an"]) # No audio

    command.extend(["-vf", f"scale={FINAL_VIDEO_WIDTH}:{FINAL_VIDEO_HEIGHT},fps={FINAL_VIDEO_FPS}", "-y", str(output_video_path)])
    
    # This is a VERY basic assembly. True synchronization of many narration parts and SFX
    # requires a much more sophisticated filter_complex graph.
    # Example:
    # ffmpeg -i clip1.mp4 -i clip2.mp4 -i narration1.wav -i sfx1.wav -filter_complex \
    # "[0:v][1:v]concat=n=2:v=1:a=0[vout]; \
    #  [2:a]adelay=1000|1000[narr1]; \
    #  [3:a]adelay=5000|5000[sfx_1]; \
    #  [narr1][sfx_1]amix=inputs=2[aout]" \
    # -map "[vout]" -map "[aout]" output.mp4
    # This script does NOT build such a complex graph dynamically yet.

    print(f"FFmpeg command: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Final video assembled at {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg video assembly failed: {e.stderr}")
    except Exception as e:
        print(f"FFmpeg video assembly failed: {e}")


# --- Main Pipeline ---
def main():
    setup_directories()

    # --- 1. Ideation (Channel & Video Concepts) ---
    print_stage("1. Generating Ideas...")
    channel_niche_prompt = "Suggest 3 unique and promising YouTube channel niches for 2025 that can be largely automated using AI tools. For each niche, provide a catchy channel name and a brief concept."
    channel_ideas_raw = llm_generate(channel_niche_prompt, system_prompt="You are a YouTube channel strategy expert.")
    
    if not channel_ideas_raw:
        print("Failed to generate channel ideas. Exiting.")
        return
    
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCRIPTS_DIR / "01_channel_ideas.txt", "w", encoding="utf-8") as f:
        f.write(channel_ideas_raw)
    print(f"Channel ideas saved to {SCRIPTS_DIR / '01_channel_ideas.txt'}")
    
    # For this script, we'll manually select one idea to proceed.
    # In a real automated system, you might parse or have the LLM choose the best.
    # Example: Assume first idea is chosen.
    # This part needs to be made dynamic if you want to choose from LLM output
    chosen_channel_name = "AI_Narrated_Wonders"
    chosen_channel_niche = "Exploring historical mysteries and scientific phenomena with AI-generated visuals and narration."
    print(f"\nSelected Channel: {chosen_channel_name} ({chosen_channel_niche})\n")

    video_topic_prompt = f"For a YouTube channel named '{chosen_channel_name}' focusing on '{chosen_channel_niche}', generate 5 compelling video topic ideas. For each, provide a potential title and a one-sentence concept."
    video_ideas_raw = llm_generate(video_topic_prompt, system_prompt="You are a creative YouTube content planner.")

    if not video_ideas_raw:
        print("Failed to generate video ideas. Exiting.")
        return

    with open(SCRIPTS_DIR / "02_video_ideas.txt", "w", encoding="utf-8") as f:
        f.write(video_ideas_raw)
    print(f"Video ideas saved to {SCRIPTS_DIR / '02_video_ideas.txt'}")

    # Manually select one video idea to proceed
    # Example: Assume first idea is chosen
    chosen_video_title = "The Lost City of Zerzura: Myth or Reality?"
    chosen_video_concept = "An AI-narrated exploration of the legends and archaeological evidence surrounding the mythical oasis city of Zerzura in the Sahara Desert."
    print(f"\nSelected Video: {chosen_video_title} ({chosen_video_concept})\n")


    # --- 2. Scripting (Detailed Video Script) ---
    print_stage("2. Generating Video Script...")
    # Aim for roughly 150 words per minute for an 8.5 minute video = ~1275 words
    script_prompt = f"""
    Create a detailed video script for a YouTube video titled "{chosen_video_title}".
    The video should be approximately 8 minutes and 30 seconds long.
    The channel is '{chosen_channel_name}' and focuses on '{chosen_channel_niche}'.
    The target audience is general viewers interested in history, mystery, and science.
    The script should include:
    1.  An engaging introduction (hook, what the video is about, what viewers will learn).
    2.  Several distinct scenes or sections (minimum 5, maximum 10).
        For each scene:
        - A clear scene heading (e.g., SCENE 1: THE LEGEND BEGINS).
        - A detailed description of the visuals to be shown (imagine AI-generated imagery: landscapes, artifacts, maps, animations).
        - Narration text for that scene.
        - Optional: Suggested sound effects in brackets (e.g., [desert wind howling], [ancient stonework crumbling]).
    3.  A concluding summary and a call to action (like, subscribe, comment).
    Ensure the narration is informative, engaging, and flows well.
    Break down complex information into digestible parts.
    The total word count for narration should be around 1200-1300 words.
    """
    video_script_raw = llm_generate(script_prompt, system_prompt="You are an expert documentary scriptwriter specializing in historical mysteries for a YouTube audience.", max_tokens=4000) # Increased max_tokens

    if not video_script_raw:
        print("Failed to generate video script. Exiting.")
        return
        
    video_script_path = SCRIPTS_DIR / "03_video_script_main.txt"
    with open(video_script_path, "w", encoding="utf-8") as f:
        f.write(video_script_raw)
    print(f"Video script saved to {video_script_path}")

    # --- 3. Parse Script for Scenes, Narration, Visuals, SFX ---
    # This is a complex parsing task. For this script, we'll assume a very specific format
    # from the LLM or use a simplified structure.
    # A more robust solution would use regex or another LLM call for structured JSON output.
    print_stage("3. Parsing Video Script...")
    
    scenes_data = []
    current_scene_heading = None
    current_visuals = ""
    current_narration = ""
    current_sfx = []

    # Basic parser - highly dependent on LLM's output format consistency
    for line in video_script_raw.split('\n'):
        line_stripped = line.strip()
        if line_stripped.startswith("SCENE ") and ":" in line_stripped:
            if current_scene_heading: # Save previous scene
                scenes_data.append({
                    "heading": current_scene_heading,
                    "visual_description": current_visuals.strip(),
                    "narration": current_narration.strip(),
                    "sfx_cues": list(current_sfx) # copy
                })
            current_scene_heading = line_stripped
            current_visuals = ""
            current_narration = ""
            current_sfx.clear()
        elif current_scene_heading:
            if "VISUALS:" in line_stripped.upper() or "DESCRIPTION:" in line_stripped.upper():
                current_visuals += line_stripped.split(":", 1)[-1].strip() + " "
            elif "NARRATION:" in line_stripped.upper():
                current_narration += line_stripped.split(":", 1)[-1].strip() + " "
            elif "SFX:" in line_stripped.upper() or "[" in line_stripped and "]" in line_stripped:
                # Simple SFX extraction
                import re
                found_sfx = re.findall(r'\[(.*?)\]', line_stripped)
                current_sfx.extend(found_sfx)
                if not found_sfx: # If SFX: was used but no brackets
                    current_narration += line_stripped + " " # Assume it's part of narration
            else: # Assume it's narration if not specified
                current_narration += line_stripped + " "
    
    if current_scene_heading: # Save the last scene
        scenes_data.append({
            "heading": current_scene_heading,
            "visual_description": current_visuals.strip(),
            "narration": current_narration.strip(),
            "sfx_cues": list(current_sfx)
        })

    if not scenes_data:
        print("Could not parse scenes from the script. Check script format. Exiting.")
        return

    parsed_script_path = SCRIPTS_DIR / "04_parsed_scenes.json"
    with open(parsed_script_path, "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=4)
    print(f"Parsed scene data saved to {parsed_script_path}")


    # --- 4. Storyboard Images ---
    print_stage("4. Generating Storyboard Images...")
    # This requires a ComfyUI workflow JSON that takes prompts and generates images.
    # Let's assume 'comfyui_workflows/yt_txt3img.json' exists.
    # You'll need to create this API workflow in ComfyUI first.
    # It should have identifiable nodes for "Positive Prompt", "Negative Prompt", "KSampler" (for seed), "Empty Latent Image" (for size).
    
    # IMPORTANT: Create this file in your COMFYUI_BASE_PATH / ComfyUI directory
    # or adjust path. It's a JSON export of your ComfyUI graph in API format.
    comfy_image_workflow_path = Path("comfyui_workflows/yt_txt3img.json") # Relative to this script

    if not comfy_image_workflow_path.exists():
        print(f"ComfyUI image workflow not found at {comfy_image_workflow_path}. Skipping image generation.")
    else:
        for i, scene in enumerate(scenes_data):
            print(f"\nGenerating storyboard for Scene {i+1}: {scene['heading']}")
            
            # Create more descriptive prompt for image generation from visual description
            image_gen_prompt_enhancement = f"Based on the scene '{scene['heading']}' and visual description '{scene['visual_description']}', generate a detailed image prompt for a cinematic, high-quality visual. Focus on key elements, atmosphere, and art style (e.g., photorealistic, epic, mysterious, ancient)."
            detailed_image_prompt = llm_generate(image_gen_prompt_enhancement, system_prompt="You are an AI assistant that creates vivid image generation prompts from scene descriptions.", temperature=0.5)

            if not detailed_image_prompt:
                detailed_image_prompt = scene['visual_description'] # Fallback

            # Generate first frame
            prompts_first = {
                "positive_prompt": f"{detailed_image_prompt}, first frame, establishing shot. cinematic lighting.",
                "negative_prompt": "text, watermark, ugly, deformed, blur, low quality",
                "seed": (i + 1) * 1000 # Consistent seed per scene start
            }
            scene["storyboard_first"] = generate_comfyui_image(comfy_image_workflow_path, prompts_first, f"scene_{i+1}_first", 0)

            # Optional: Generate last frame (could be similar or a variation)
            prompts_last = {
                "positive_prompt": f"{detailed_image_prompt}, final frame of scene, sense of conclusion or transition. cinematic lighting.",
                "negative_prompt": "text, watermark, ugly, deformed, blur, low quality",
                "seed": (i + 1) * 1000 + 1 # Slightly different seed for variation
            }
            scene["storyboard_last"] = generate_comfyui_image(comfy_image_workflow_path, prompts_last, f"scene_{i+1}_last", 1)
            
            # Optional: Middle frame (if needed, could use interpolation concepts or just another prompt)
            # scene["storyboard_middle"] = ...

    updated_parsed_script_path = SCRIPTS_DIR / "05_scenes_with_storyboards.json"
    with open(updated_parsed_script_path, "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=4)
    print(f"Scene data with storyboard paths saved to {updated_parsed_script_path}")


    # --- 5. Video Clips (LTX-Video via ComfyUI) ---
    print_stage("5. Generating Video Clips...")
    # This requires a ComfyUI LTX-Video workflow, e.g., image-to-video.
    # Assume 'comfyui_workflows/ltx_img2vid_api.json'
    comfy_video_workflow_path = Path("comfyui_workflows/ltx_img2vid_api.json") # Relative

    if not comfy_video_workflow_path.exists():
        print(f"ComfyUI LTX-Video workflow not found at {comfy_video_workflow_path}. Skipping video clip generation.")
    else:
        generated_video_clip_paths = []
        for i, scene in enumerate(scenes_data):
            if scene.get("storyboard_first"):
                # LTX-Video often works best with one strong starting image.
                # You could also feed it storyboard_first, middle, last if your workflow supports it (e.g. keyframes)
                storyboard_frames_for_clip = [scene["storyboard_first"]]
                if scene.get("storyboard_last") and scene["storyboard_first"] != scene["storyboard_last"]: # if distinct last frame
                     # A more complex workflow might use first and last for interpolation
                     pass # For simple img2vid, first frame is often enough to kickstart

                clip_name = f"scene_{i+1}_clip.mp4"
                video_path = generate_comfyui_video_clip(comfy_video_workflow_path, storyboard_frames_for_clip, clip_name, i+1, 0)
                if video_path:
                    generated_video_clip_paths.append(video_path)
                    scene["video_clip_path"] = video_path # Store for assembly
            else:
                print(f"Skipping video clip for Scene {i+1} due to missing storyboard.")
        
        with open(SCRIPTS_DIR / "06_scenes_with_videos.json", "w", encoding="utf-8") as f:
            json.dump(scenes_data, f, indent=4)
        print(f"Scene data with video clip paths saved.")


    # --- 6. Voice-over (TTS) & Timestamping ---
    print_stage("6. Generating Narration Audio & Timestamps...")
    narration_segments_for_assembly = []
    full_narration_text = ""
    narration_audio_files = []

    for i, scene in enumerate(scenes_data):
        if scene["narration"]:
            narration_text = scene["narration"]
            full_narration_text += narration_text + " " # For full transcript later
            audio_filename = f"scene_{i+1}_narration.wav"
            narration_audio_path = generate_tts_audio(narration_text, audio_filename)
            if narration_audio_path:
                scene["narration_audio_path"] = narration_audio_path
                narration_audio_files.append(narration_audio_path)
                # For simplicity, we'll timestamp the whole narration later.
                # A more granular approach would timestamp per scene narration.
            else:
                print(f"Failed to generate narration for scene {i+1}")
    
    # Combine all narration audios into one for easier ASR timestamping
    # Or, if you prefer per-scene timing, call get_word_timestamps_from_audio for each scene["narration_audio_path"]
    # and scene["narration"]. This script simplifies to one global narration track for now.
    
    main_narration_output_path = NARRATION_DIR / "full_narration_combined.wav"
    if len(narration_audio_files) > 1:
        concat_narration_list = WORKSPACE_DIR / "ffmpeg_narration_concat_list.txt"
        with open(concat_narration_list, "w") as f:
            for audio_f in narration_audio_files:
                f.write(f"file '{Path(audio_f).resolve()}'\n")
        
        ffmpeg_concat_audio_cmd = [
            FFMPEG_PATH, "-f", "concat", "-safe", "0", "-i", str(concat_narration_list),
            "-c", "copy", "-y", str(main_narration_output_path)
        ]
        try:
            subprocess.run(ffmpeg_concat_audio_cmd, check=True, capture_output=True)
            print(f"Combined narration saved to {main_narration_output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to combine narration tracks: {e.stderr.decode()}")
            main_narration_output_path = None # Failed
    elif len(narration_audio_files) == 1:
        shutil.copy(narration_audio_files[0], main_narration_output_path)
        print(f"Narration (single file) copied to {main_narration_output_path}")
    else:
        main_narration_output_path = None
        print("No narration audio generated.")

    timed_narration_script = []
    if main_narration_output_path and Path(main_narration_output_path).exists() and full_narration_text.strip():
        print("Attempting to get timestamps for the full narration...")
        timed_narration_script = get_word_timestamps_from_audio(str(main_narration_output_path), full_narration_text.strip())
        if timed_narration_script:
            with open(SCRIPTS_DIR / "07_timed_narration_script.json", "w", encoding="utf-8") as f:
                json.dump(timed_narration_script, f, indent=4)
            print(f"Timed narration script saved.")
            # For assembly, we'd use the main_narration_output_path and assume it starts at 0.
            # If per-scene timing was done, logic here would be different.
            narration_segments_for_assembly.append({
                "audio_path": str(main_narration_output_path),
                "start_time": 0 # Assuming starts at the beginning
            })
        else:
            print("Failed to get timestamps. Narration will not be timed for assembly.")
            # Still add the untimed audio if it exists
            narration_segments_for_assembly.append({
                "audio_path": str(main_narration_output_path),
                "start_time": 0
            })
    
    with open(SCRIPTS_DIR / "08_scenes_with_narration_audio.json", "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=4)


    # --- 7. Sound Effects ---
    print_stage("7. Generating Sound Effects...")
    sfx_items_for_assembly = []
    # This part requires knowing WHEN each SFX should play.
    # The simple script parser above just lists cues per scene.
    # A more advanced system would:
    #   1. Have the LLM output SFX cues with approximate timing within the scene's narration.
    #   2. Use the word timestamps from narration to calculate absolute SFX start times.
    # For this script, we'll generate SFX but not accurately time them for assembly without more info.
    
    sfx_time_offset_within_scene = 0 # Placeholder
    for i, scene in enumerate(scenes_data):
        scene_start_time_in_video = sum(video_durations[:i]) # Approximate scene start

        for cue_index, sfx_cue in enumerate(scene.get("sfx_cues", [])):
            if sfx_cue: # Ensure cue is not empty
                sfx_filename = f"scene_{i+1}_sfx_{cue_index}_{sfx_cue.replace(' ','_')[:20]}.wav" # Sanitize
                sfx_audio_path = generate_sfx_audio(sfx_cue, sfx_filename)
                if sfx_audio_path:
                    scene.setdefault("sfx_audio_paths", []).append(sfx_audio_path)
                    # Placeholder timing: SFX starts a bit into the scene, or after previous SFX in same scene
                    # THIS IS A MAJOR SIMPLIFICATION. Real timing needs to come from script or ASR alignment.
                    approx_sfx_start_time = scene_start_time_in_video + sfx_time_offset_within_scene
                    sfx_items_for_assembly.append({
                        "audio_path": sfx_audio_path,
                        "start_time": approx_sfx_start_time # Needs to be absolute time in final video
                    })
                    sfx_time_offset_within_scene += 3 # Assume SFX are ~3s and play sequentially for now
        sfx_time_offset_within_scene = 0 # Reset for next scene

    with open(SCRIPTS_DIR / "09_scenes_with_sfx_audio.json", "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=4)


    # --- 8. Assembly (Video Editing) ---
    print_stage("8. Assembling Final Video...")
    final_video_filename = f"{chosen_channel_name.replace(' ','_')}_{chosen_video_title.replace(' ','_')[:30]}.mp4"
    final_output_path = FINAL_VIDEO_DIR / final_video_filename

    # Reload video clip paths if they were generated
    video_clips_for_assembly = []
    if (SCRIPTS_DIR / "06_scenes_with_videos.json").exists():
        with open(SCRIPTS_DIR / "06_scenes_with_videos.json", "r", encoding="utf-8") as f:
            scenes_data_with_videos = json.load(f)
        for scene in scenes_data_with_videos:
            if scene.get("video_clip_path") and Path(scene["video_clip_path"]).exists():
                video_clips_for_assembly.append(scene["video_clip_path"])
    
    if not video_clips_for_assembly:
        print("No video clips found to assemble. Exiting assembly.")
        return

    assemble_final_video(video_clips_for_assembly, narration_segments_for_assembly, sfx_items_for_assembly, final_output_path)

    print_stage("Pipeline Finished.")

def print_stage(title):
    print("\n" + "="*10 + f" {title} " + "="*10)

if __name__ == "__main__":
    # --- Pre-flight checks for ComfyUI workflow files ---
    # User needs to create these JSON API workflow files from their ComfyUI setup.
    # This script refers to them but doesn't create them.
    required_comfy_workflows = [
        "comfyui_workflows/yt_txt3img.json",
        "comfyui_workflows/ltx_img2vid_api.json"
    ]
    missing_workflows = False
    for wf_path_str in required_comfy_workflows:
        wf_path = Path(wf_path_str)
        if not wf_path.exists():
            print(f"CRITICAL ERROR: ComfyUI workflow file not found: {wf_path.resolve()}")
            print("Please create this API workflow JSON in ComfyUI and save it to the specified path.")
            missing_workflows = True
    if missing_workflows:
        print("Exiting due to missing ComfyUI workflow files.")
    else:
        main()