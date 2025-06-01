import re
from tqdm import tqdm
from config import *
from generate import *

# --- 3. Narration ---
def create_voice(project):
    i = 0
    if project.resume:
        narration_files = list(project.directories["narration"].glob("*.*"))
        if narration_files:
            narration_files.sort()
            for file in narration_files:
                project.episode.nar_audio.append(file)
            i = len(narration_files)
            if i >= len(project.episode.narrations):
                print("All narrations already synthesized. Skipping.")
                return
            print(f"Resuming narration Synthesizing at index {i}.")

    print_stage("3. Synthesizing Narration...")
    
    for i in tqdm(range(i, len(project.episode.narrations)), desc="Generating prompts", unit="narration"):
        output_file = generate_voice(project, project.episode.narrations[i])
        output_path = project.directories["narration"] / (f"{i:03d}" + output_file.suffix)
        output_file.rename(output_path)
        project.episode.nar_audio.append(output_path)




# --- 4. Storyboard Images ---
def create_frames(project):
    i = 0
    if project.resume:
        image_files = list(project.directories["storyboard"].glob("*.png"))
        if image_files:
            image_files.sort()
            for file in image_files:
                project.episode.images.append(file)
            i = len(image_files)
            if i >= len(project.episode.img_prompts):
                print("All storyboard images already generated. Skipping.")
                return
            print(f"Resuming storyboard image generation at index {i}.")

    print_stage("4.5 Generating Storyboard Images...")

    for i in tqdm(range(i, len(project.episode.img_prompts)), desc="Generating Images", unit="Image"):
        image = generate_comfyui_image(project, project.episode.img_prompts[i], f"Image_{i:04d}.png")

        if not image:
            exit(f"Failed to generate image for prompt: {project.episode.img_prompts[i]}")
        
        project.episode.images.append(image)



# --- 5. Video Clips (LTX-Video via ComfyUI) ---
def create_video(scenes_data):
    print_stage("5. Generating Video Clips...")
    # This requires a ComfyUI LTX-Video workflow, e.g., image-to-video.
    # Assume 'comfyui_workflows/ltx_img2vid_api.json'

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