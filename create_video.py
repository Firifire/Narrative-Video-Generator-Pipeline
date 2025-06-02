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
        image = generate_comfyui_image(project, project.episode.img_prompts[i], f"Image_{i:04d}")

        if not image:
            exit(f"Failed to generate image for prompt: {project.episode.img_prompts[i]}")
        
        project.episode.images.append(image)




# --- 5. Video Clips (LTX-Video via ComfyUI) ---
def create_video(project):
    i = 0
    if project.resume:
        video_files = list(project.directories["video_clips"].glob("*.mp4"))
        if video_files:
            video_files.sort()
            for file in video_files:
                project.episode.video_clips.append(file)
            i = len(video_files)
            if i >= len(project.episode.img_prompts):
                print("All video clips already generated. Skipping.")
                return
            print(f"Resuming video generation at index {i}.")
    
    print_stage("5. Generating Video Clips...")

    for i in tqdm(range(i, len(project.episode.img_prompts)), desc="Generating Animations", unit="Clip"):
            video = generate_comfyui_video_clip(project, project.episode.images[i], project.episode.img_prompts[i], f"clip_{i:04d}")

            if not video:
                exit(f"Failed to generate video for image: {project.episode.images[i]}")

            project.episode.video_clips.append(video)
