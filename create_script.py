import re
from config import *
from generate import *


# --- 1. Ideation (Channel & Video Concepts) ---
def create_channel():
    global chosen_channel_name, chosen_channel_niche

    print_stage("1. Generating Ideas...")
    channel_niche_prompt = "Suggest 3 unique and promising YouTube channel niches for 2025 that can be largely automated using AI tools. For each niche, provide a catchy channel name and a brief concept."
    channel_ideas_raw = llm_generate(channel_niche_prompt, system_prompt="You are a YouTube channel strategy expert.")
    
    if not channel_ideas_raw:
        print("Failed to generate channel ideas. Exiting.")
        exit()
    
    with open(SCRIPTS_DIR / "01_channel_ideas.txt", "w", encoding="utf-8") as f:
        f.write(channel_ideas_raw)
    print(f"Channel ideas saved to {SCRIPTS_DIR / '01_channel_ideas.txt'}")
  
    # For this script, we'll manually select one idea to proceed.
    # In a real automated system, you might parse or have the LLM choose the best.
    # Example: Assume first idea is chosen.
    # This part needs to be made dynamic if you want to choose from LLM output
    chosen_channel_name = "AI_Narrated_Wonders"
    chosen_channel_niche = "Exploring historical mysteries and scientific phenomena with AI-generated visuals and narration."

def create_title():
    global chosen_video_title, chosen_video_concept

    print(f"\nSelected Channel: {chosen_channel_name} ({chosen_channel_niche})\n")

    video_topic_prompt = f"For a YouTube channel named '{chosen_channel_name}' focusing on '{chosen_channel_niche}', generate 5 compelling video topic ideas. For each, provide a potential title and a one-sentence concept."
    video_ideas_raw = llm_generate(video_topic_prompt, system_prompt="You are a creative YouTube content planner.")

    if not video_ideas_raw:
        print("Failed to generate video ideas. Exiting.")
        exit()

    with open(SCRIPTS_DIR / "02_video_ideas.txt", "w", encoding="utf-8") as f:
        f.write(video_ideas_raw)
    print(f"Video ideas saved to {SCRIPTS_DIR / '02_video_ideas.txt'}")

    # Manually select one video idea to proceed
    # Example: Assume first idea is chosen
    chosen_video_title = "The Lost City of Zerzura: Myth or Reality?"
    chosen_video_concept = "An AI-narrated exploration of the legends and archaeological evidence surrounding the mythical oasis city of Zerzura in the Sahara Desert."

def create_script():
    print(f"\nSelected Video: {chosen_video_title} ({chosen_video_concept})\n")
    # --- 2. Scripting (Detailed Video Script) ---
    print_stage("2. Generating Video Script...")
    # Aim for roughly 150 words per minute for an 8.5 minute video = ~1275 words
    script_prompt = f"""
    Create a detailed video script for a YouTube video titled "{chosen_video_title}".
    The video should be minimum 8 minutes and 30 seconds long.
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
    4.  Format Should be
        SCENE_1_NAME
        VISUALS: [description of visuals]
        NARRATION: [narration text]

        SCENE_2_NAME
        VISUALS: [description of visuals]
        NARRATION: [narration text]
    """
    video_script_raw = llm_generate(script_prompt, system_prompt="You are an expert documentary scriptwriter specializing in historical mysteries for a YouTube audience.", max_tokens=4000) # Increased max_tokens

    if not video_script_raw:
        print("Failed to generate video script. Exiting.")
        exit()

    video_script_raw = video_script_raw.replace('*', '') # Remove any unwanted characters
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
            if "VISUALS:" in line_stripped.upper():
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
        exit()

    parsed_script_path = SCRIPTS_DIR / "04_parsed_scenes.json"
    with open(parsed_script_path, "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=4)
    print(f"Parsed scene data saved to {parsed_script_path}")
    return scenes_data

def create_img_prompts(scenes_data):
    # --- 4. Storyboard Images ---
    print_stage("4.0 Generating Storyboard Images...")

    # IMPORTANT: Create this file in your COMFYUI_BASE_PATH / ComfyUI directory
    # or adjust path. It's a JSON export of your ComfyUI graph in API format.
    comfy_image_workflow_path = Path("comfyui_workflows/yt_txt3img.json") # Relative to this script

    prompts_first = []

    if not comfy_image_workflow_path.exists():
        print(f"ComfyUI image workflow not found at {comfy_image_workflow_path}. Skipping image generation.")
    else:
        for i, scene in enumerate(scenes_data):
            print(f"\nGenerating prompt {i+1}: {scene['heading']}")
            
            # Create more descriptive prompt for image generation from visual description
            image_gen_prompt_enhancement = f"Based on the scene '{scene['heading']}' and visual description '{scene['visual_description']}', generate a detailed image prompt for a cinematic, high-quality visual. Focus on key elements, atmosphere, and art style (e.g., photorealistic, epic, mysterious, ancient)."
            detailed_image_prompt = llm_generate(image_gen_prompt_enhancement, system_prompt="You are an AI assistant that creates vivid image generation prompts from scene descriptions.", temperature=0.5)

            if not detailed_image_prompt:
                detailed_image_prompt = scene['visual_description'] # Fallback

            # Generate first frame
            prompts_first.append({
                "positive_prompt": f"{detailed_image_prompt}, first frame, establishing shot. cinematic lighting.",
                "negative_prompt": "text, watermark, ugly, deformed, blur, low quality",
                "seed": (i + 1) * 1000 # Consistent seed per scene start
            })

            # Optional: Generate last frame (could be similar or a variation)
            # prompts_last = {
            #     "positive_prompt": f"{detailed_image_prompt}, final frame of scene, sense of conclusion or transition. cinematic lighting.",
            #     "negative_prompt": "text, watermark, ugly, deformed, blur, low quality",
            #     "seed": (i + 1) * 1000 + 1 # Slightly different seed for variation
            # }
            
            # Optional: Middle frame (if needed, could use interpolation concepts or just another prompt)
            # scene["storyboard_middle"] = ...
    return prompts_first