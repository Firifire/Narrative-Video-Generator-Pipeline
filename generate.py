from config import *
import os
import json
import subprocess
import requests
import websocket
import uuid
import json
import time
import os
import shutil
from pathlib import Path
import urllib.parse

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
    


from kokoro import KPipeline
import soundfile as sf    
vPipeline = KPipeline(lang_code=KOKORO_LANG)
def generate_voice(project, text):
    """Generates audio files for narration using Kokoro TTS."""

    clean_workspace(project)

    generator = vPipeline(text, voice=KOKORO_VOICE_NAME)

    audio_files = []
    for i, (gs, ps, audio) in enumerate(generator):
        output_path = project.directories["workspace"] / f"narration_{i:03d}.wav"
        sf.write(output_path, audio, 24000)
        audio_files.append(Path(output_path))

    return merge_audio_files(audio_files)


def generate_comfyui_image(project, input_prompts, output_prefix):
    """
    Triggers a ComfyUI workflow to generate an image and downloads it.
    Assumes TXT2IMG_WORKFLOW is a ComfyUI API format JSON.
    Input_prompts is a dictionary to update specific nodes in the workflow.
    """
    client_id = str(uuid.uuid4())

    try:
        with open(TXT2IMG_WORKFLOW, 'r') as f:
            prompt_workflow = json.load(f)

        for node_id, node_data in prompt_workflow.items():
            meta_title = node_data.get("_meta", {}).get("title")
            if meta_title == "CLIP Text Encode (Positive Prompt)":
                prompt_workflow[node_id]["inputs"]["text"] = input_prompts["image"]
            # elif meta_title == "Negative Prompt":
            #     prompt_workflow[node_id]["inputs"]["text"] = input_prompts.get("negative_prompt", "ugly, bad anatomy")
            # elif meta_title == "Empty Latent Image": # Common for image size
            #     # Assuming IMAGE_WIDTH and IMAGE_HEIGHT are globally defined or passed via input_prompts
            #     if "IMAGE_WIDTH" in globals() and "IMAGE_HEIGHT" in globals():
            #         prompt_workflow[node_id]["inputs"]["width"] = IMAGE_WIDTH
            #         prompt_workflow[node_id]["inputs"]["height"] = IMAGE_HEIGHT
            elif meta_title == "KSampler": # Common for sampler settings
                # Assuming these are globally defined or passed via input_prompts
                if "IMAGE_STEPS" in globals():
                    prompt_workflow[node_id]["inputs"]["steps"] = IMAGE_STEPS
                if "IMAGE_CFG" in globals():
                    prompt_workflow[node_id]["inputs"]["cfg"] = IMAGE_CFG
                if "IMAGE_SAMPLER" in globals():
                    prompt_workflow[node_id]["inputs"]["sampler_name"] = IMAGE_SAMPLER
                if "IMAGE_SCHEDULER" in globals():
                    prompt_workflow[node_id]["inputs"]["scheduler"] = IMAGE_SCHEDULER
                prompt_workflow[node_id]["inputs"]["seed"] = input_prompts.get("seed", int(time.time())) # Use provided seed or a new one

        # Step 1: Queue the prompt using HTTP POST to /prompt [1, 2]
        http_server_address = f"http://{COMFYUI_SERVER_URL}"
        prompt_payload = {"prompt": prompt_workflow, "client_id": client_id}
        
        debug_print(f"Queueing prompt for {output_prefix} with client_id: {client_id}")
        response = requests.post(f"{http_server_address}/prompt", json=prompt_payload)
        response.raise_for_status()
        prompt_response_data = response.json()

        if "error" in prompt_response_data:
            node_errors = prompt_response_data.get("node_errors", {})
            error_messages = [f"Node {ne_id}: {ne_details.get('errors', [{}]).get('message', 'Unknown error')}" for ne_id, ne_details in node_errors.items()]
            exit(f"ComfyUI error when queueing prompt: {prompt_response_data['error']}. Details: {'; '.join(error_messages)}")
            
        prompt_id = prompt_response_data.get("prompt_id")
        if not prompt_id:
            exit(f"Failed to get prompt_id from ComfyUI for {output_prefix}. Response: {prompt_response_data}")
        
        debug_print(f"Prompt queued successfully. Prompt ID: {prompt_id}")

        # Step 2: Connect to WebSocket for status updates [1, 2]
        ws_server_address = f"ws://{COMFYUI_SERVER_URL}/ws?clientId={client_id}"
        ws = websocket.WebSocket()
        ws.connect(ws_server_address)
        debug_print(f"WebSocket connected for {output_prefix}")

        image_downloaded = False
        output_image_path = None

        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                # print(f"WS Message: {message}") # For debugging
                if message.get("type") == "executing":
                    data = message.get("data", {})
                    if data.get("node") is None and data.get("prompt_id") == prompt_id:
                        debug_print(f"Execution started for prompt_id: {prompt_id}")
                
                elif message.get("type") == "executed" and message.get("data", {}).get("prompt_id") == prompt_id:
                    data = message.get("data", {})
                    outputs = data.get("output", {})
                    if not outputs:
                        continue
                    debug_print(f"Execution finished for prompt_id: {prompt_id}. Outputs received.")
                    
                    # Step 3: Retrieve image(s) from outputs [1, 2]
                    for node_id_output, node_output_data in outputs.items():
                        if "images" in node_id_output:
                            for image_data in node_output_data:
                                filename = image_data.get("filename")
                                subfolder = image_data.get("subfolder", "")
                                img_type = image_data.get("type", "output")

                                if not filename:
                                    continue

                                # Download the image using /view endpoint [1, 2]
                                view_url = f"{http_server_address}/view?filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type={img_type}"
                                print(f"Downloading image: {filename} from {view_url}")
                                
                                img_response = requests.get(view_url)
                                img_response.raise_for_status()

                                
                                output_path_obj = project.directories["storyboard"] / f"{output_prefix}.png"
                                with open(output_path_obj, 'wb') as f_img:
                                    f_img.write(img_response.content)
                                
                                debug_print(f"Image saved to {output_path_obj}")
                                output_image_path = str(output_path_obj)
                                image_downloaded = True
                                break # Downloaded one image, exit loop
                        if image_downloaded:
                            break
                    ws.close()
                    return output_image_path # Return path of the first successfully downloaded image

                elif message.get("type") == "execution_error" and message.get("data", {}).get("prompt_id") == prompt_id:
                    error_data = message.get("data", {})
                    print(f"Execution error for prompt_id {prompt_id}: {error_data}")
                    ws.close()
                    exit()

    except requests.exceptions.RequestException as e:
        print(f"ComfyUI HTTP request failed for {output_prefix}: {e}")
        exit(f"Response: {response.text if 'response' in locals() else 'No response'}")
    except websocket.WebSocketException as e:
        exit(f"ComfyUI WebSocket communication failed for {output_prefix}: {e}")
    except json.JSONDecodeError as e:
        exit(f"Failed to decode JSON from ComfyUI for {output_prefix}: {e}")
    except Exception as e:
        exit(f"ComfyUI image generation failed for {output_prefix}: {e}")
    finally:
        if 'ws' in locals() and ws.connected:
            ws.close()
            print("WebSocket closed in finally block.")


def generate_comfyui_video_clip(project, image_path, input_prompt, output_video_name):
    """
    Triggers a ComfyUI LTX-Video workflow.
    Assumes IMG2VID_WORKFLOW points to an LTX-Video API workflow.
    image_paths is a list of paths to storyboard frames for the clip.
    """

    client_id = str(uuid.uuid4())

    try:
        with open(IMG2VID_WORKFLOW, 'r', encoding='utf-8') as f:
            prompt_workflow = json.load(f)
        
        # Calculate the number of frames based FPS and input_prompt["duration"]
        num_frames = int(input_prompt["duration"] * VIDEO_CLIP_FPS)
        if num_frames > VIDEO_CLIP_MAX_FRAMES:
            print(f"Warning: Duration {input_prompt['duration']} exceeds max frames {VIDEO_CLIP_MAX_FRAMES}. Clamping to max.")
            num_frames = VIDEO_CLIP_MAX_FRAMES
        # num_frame must multiple of 8 + 1
        if (num_frames - 1) % 8 != 0:
            num_frames = ((num_frames - 1) // 8 + 1) * 8 + 1
            debug_print(f"Adjusted number of frames to {num_frames} to be multiple of 8 + 1.")

        for node_id, node_data in prompt_workflow.items():
            if node_data.get("_meta", {}).get("title") == "Load Image":
                prompt_workflow[node_id]["inputs"]["image"] = str(image_path.resolve())
            if node_data.get("_meta", {}).get("title") == "CLIP Text Encode (Positive Prompt)":
                prompt_workflow[node_id]["inputs"]["text"] = input_prompt["video"]
            if node_data.get("_meta", {}).get("title") == "LTXV Base Sampler":
                prompt_workflow[node_id]["inputs"]["num_frames"] = num_frames
            if node_data.get("_meta", {}).get("title") == "LTXVConditioning":
                prompt_workflow[node_id]["inputs"]["frame_rate"] = VIDEO_CLIP_FPS
            if node_data.get("_meta", {}).get("title") == "Video Combine":
                prompt_workflow[node_id]["inputs"]["filename_prefix"] = output_video_name
                prompt_workflow[node_id]["inputs"]["frame_rate"] = VIDEO_CLIP_FPS

        http_server_address = f"http://{COMFYUI_SERVER_URL}"
        prompt_payload = {"prompt": prompt_workflow, "client_id": client_id}
        
        debug_print(f"Sent LTX-Video generation request to ComfyUI for {output_video_name}")
        response = requests.post(f"{http_server_address}/prompt", json=prompt_payload)
        response.raise_for_status()
        prompt_response_data = response.json()

        if "error" in prompt_response_data:
            node_errors = prompt_response_data.get("node_errors", {})
            error_messages = [f"Node {ne_id}: {ne_details.get('errors', [{}]).get('message', 'Unknown error')}" for ne_id, ne_details in node_errors.items()]
            exit(f"ComfyUI error when queueing prompt: {prompt_response_data['error']}. Details: {'; '.join(error_messages)}")
        
        prompt_id = prompt_response_data.get("prompt_id")
        if not prompt_id:
            exit(f"Failed to get prompt_id from ComfyUI for {output_video_name}. Response: {prompt_response_data}")
        
        debug_print(f"Prompt queued successfully. Prompt ID: {prompt_id}")

        # Step 2: Connect to WebSocket for status updates [1, 2]
        ws_server_address = f"ws://{COMFYUI_SERVER_URL}/ws?clientId={client_id}"
        ws = websocket.WebSocket()
        ws.connect(ws_server_address)
        debug_print(f"WebSocket connected for {output_video_name}")

        video_downloaded = False
        output_video_path = None

        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                # print(f"WS Message: {message}") # For debugging
                if message.get("type") == "executing":
                    data = message.get("data", {})
                    if data.get("node") is None and data.get("prompt_id") == prompt_id:
                        debug_print(f"Execution started for prompt_id: {prompt_id}")
                
                elif message.get("type") == "executed" and message.get("data", {}).get("prompt_id") == prompt_id:
                    data = message.get("data", {})
                    outputs = data.get("output", {})
                    if not outputs:
                        continue
                    debug_print(f"Execution finished for prompt_id: {prompt_id}. Outputs received.")
                    
                    # Step 3: Retrieve video(s) from outputs [1, 2]
                    for node_id_output, node_output_data in outputs.items():
                        if "gifs" in node_id_output:
                            for video_data in node_output_data:
                                filename = video_data.get("filename")
                                subfolder = video_data.get("subfolder", "")
                                img_type = video_data.get("type", "output")

                                if not filename:
                                    continue

                                # Download the video using /view endpoint [1, 2]
                                view_url = f"{http_server_address}/view?filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type={img_type}"
                                debug_print(f"Downloading video: {filename} from {view_url}")
                                
                                img_response = requests.get(view_url)
                                img_response.raise_for_status()

                                output_path_obj = project.directories["video_clips"] / f"{output_video_name}.mp4"
                                with open(output_path_obj, 'wb') as f_img:
                                    f_img.write(img_response.content)
                                
                                debug_print(f"video saved to {output_path_obj}")
                                output_video_path = str(output_path_obj)
                                video_downloaded = True
                                break # Downloaded one video, exit loop
                        if video_downloaded:
                            break
                    ws.close()
                    return output_video_path # Return path of the first successfully downloaded image

                elif message.get("type") == "execution_error" and message.get("data", {}).get("prompt_id") == prompt_id:
                    error_data = message.get("data", {})
                    print(f"Execution error for prompt_id {prompt_id}: {error_data}")
                    ws.close()
                    exit()
            
    except requests.exceptions.RequestException as e:
        print(f"ComfyUI HTTP request failed for {output_video_name}: {e}")
        exit(f"Response: {response.text if 'response' in locals() else 'No response'}")
    except websocket.WebSocketException as e:
        exit(f"ComfyUI WebSocket communication failed for {output_video_name}: {e}")
    except json.JSONDecodeError as e:
        exit(f"Failed to decode JSON from ComfyUI for {output_video_name}: {e}")
    except Exception as e:
        exit(f"ComfyUI LTX-Video generation failed for {output_video_name}: {e}")
    finally:
        if 'ws' in locals() and ws.connected:
            ws.close()
            print("WebSocket closed in finally block.")


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