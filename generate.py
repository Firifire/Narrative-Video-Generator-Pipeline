from config import *
import os
import json
import subprocess

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