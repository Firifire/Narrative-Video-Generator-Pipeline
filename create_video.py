import re
from config import *
from generate import *

# --- 3. Narration ---
def create_voice(project):
    i = 0
    if project.resume:
        narration_files = list(project.directories["narration"].glob("*.*"))
        if narration_files:
            i = len(narration_files)
            if i != 0:
                print(f"Resuming narration Synthesizing at index {i}.")
            elif i == len(project.episode.narrations):
                print("All narrations already synthesized. Skipping.")
                return

    print_stage("3. Synthesizing Narration...")
    
    for i in range(i, len(project.episode.narrations)):
        output_file = generate_voice(project, project.episode.narrations[i])
        output_path = project.directories["narration"] / (f"{i:03d}" + output_file.suffix)
        if output_file:
            output_file.rename(output_path)


    

# --- 4. Storyboard Images ---
def create_frames(scenes_data, prompts_first):
    print_stage("4.5 Generating Storyboard Images...")
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
            print(f"\nGenerating storyboard {i+1}: {scene['heading']}")

            scene["storyboard_first"] = generate_comfyui_image(comfy_image_workflow_path, prompts_first[i], f"scene_{i+1}_first", 0)

            # Optional: Generate last frame (could be similar or a variation)
            # scene["storyboard_last"] = generate_comfyui_image(comfy_image_workflow_path, prompts_last, f"scene_{i+1}_last", 1)
            
            # Optional: Middle frame (if needed, could use interpolation concepts or just another prompt)
            # scene["storyboard_middle"] = ...

    updated_parsed_script_path = SCRIPTS_DIR / "05_scenes_with_storyboards.json"
    with open(updated_parsed_script_path, "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=4)
    print(f"Scene data with storyboard paths saved to {updated_parsed_script_path}")


# --- 5. Video Clips (LTX-Video via ComfyUI) ---
def create_video(scenes_data):
    print_stage("5. Generating Video Clips...")
    # This requires a ComfyUI LTX-Video workflow, e.g., image-to-video.
    # Assume 'comfyui_workflows/ltx_img2vid_api.json'
    comfy_video_workflow_path = Path("comfyui_workflows/ltx_img2vid_api.json") # Relative

    if not comfy_video_workflow_path.exists():
        print(f"ComfyUI LTX-Video workflow not found at {comfy_video_workflow_path}. Skipping video clip generation.")
    else:
        generated_video_clip_paths = []
        for i, scene in enumerate(scenes_data):
            print(f"\nGenerating clip {i+1}: {scene['heading']}")
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