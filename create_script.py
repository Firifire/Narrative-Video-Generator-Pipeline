import re
from pydub.utils import mediainfo
from tqdm import tqdm
from project import *
from generate import *


# --- 1. Ideation (Channel & Video Concepts) ---
def create_channel(project):
    if not project.create_new:
        with open(project.base / project.project_name / "channel_info.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) < 2:
                exit("Channel info file is incomplete. Exiting.")
            project.project_name = lines[0].strip()
            project.niche = lines[1].strip()
        return
    
    print_stage("0. Generating Channel Idea...")
    channel_niche_prompt = "Decide on good idea a YouTube channel will focus that will be successful and create a unique channel for it.\n" \
    "Put the channel name and idea in this format:\n" \
    "[Name: Channel_Name]\n" \
    "[Niche: Channel_Niche]\n"
    channel_ideas_raw = llm_generate(channel_niche_prompt, system_prompt="You are a YouTube channel strategy expert.")
    
    if not channel_ideas_raw:
        exit("Failed to generate channel ideas. Exiting.")

    # Extract channel name
    project.project_name = extract_result(channel_ideas_raw, "Name")
    project.niche = extract_result(channel_ideas_raw, "Niche")
    if not project.project_name or not project.niche:
        exit("Failed to extract channel name or niche from generated ideas. Exiting.")
    
    project_dir = project.base / project.project_name
    project_dir.mkdir(exist_ok=True)
    with open(project_dir / "channel_info.txt", "w", encoding="utf-8") as f:
        f.write(project.project_name + "\n")
        f.write(project.niche + "\n")
    with open(project_dir / "channel_idea.txt", "w", encoding="utf-8") as f:
        f.write(channel_ideas_raw)

    print(f"Channel Info created:\nName: {project.project_name}\nNiche: {project.niche}")
    
# --- 1.1. Video Idea (Title & Concept) ---
def create_title(project):
    if project.resume and (project.directories["episode"] / "video_idea.txt").exists():
        with open(project.directories["episode"] / "video_idea.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) < 2:
                exit("Video idea file is incomplete. Exiting.")
            project.episode.name = lines[0].strip()
            project.episode.concept = lines[1].strip()
        print(f"Resuming with existing video idea: {project.episode.name}")
        return

    print_stage("1. Generating Video Idea...")

    video_topic_prompt = f"For a YouTube channel named '{project.project_name}' focusing on '{project.niche}', generate a compelling video topic idea. Provide a potential title and a one-sentence concept.\n" \
    "Format the output as:\n" \
    "[Title: Video_Title]\n" \
    "[Concept: Video_Concept]"
    video_ideas_raw = llm_generate(video_topic_prompt, system_prompt="You are a creative YouTube content planner.")

    if not video_ideas_raw:
        exit("Failed to generate video ideas. Exiting.")

    project.episode.name = extract_result(video_ideas_raw, "Title")
    project.episode.concept = extract_result(video_ideas_raw, "Concept")

    with open(project.directories["episode"] / "video_idea.txt", "w", encoding="utf-8") as f:
        f.write(project.episode.name + "\n")
        f.write(project.episode.concept + "\n")
    print(f"Video Idea created:\nTitle: {project.episode.name}")


# --- 2. Scripting (Detailed Video Script) ---
def create_script(project):
    if project.resume and (project.directories["scripts"] / "narration.txt").exists():
        with open(project.directories["scripts"] / "narration.txt", "r", encoding="utf-8") as f:
            project.episode.narrations = [line.strip() for line in f if line.strip()]
        print("Resuming with existing narration script.")
        return
    print_stage("2. Generating Video Script...")

    #    The target audience is general viewers interested in history, mystery, and science.
    #    The total word count for narration should be around 1200-1300 words.
    script_prompt = f"""
    Create a detailed video Narration script for a YouTube video titled "{project.episode.name}".
    'Concept: {project.episode.concept}'.
    The video should be minimum 8 minutes and 30 seconds long.
    The channel is '{project.project_name}' and focuses on '{project.niche}'.
    The script should include:
    1.  An engaging introduction (hook, what the video is about, what viewers will learn).
    2.  Rest of the Narration. AI Generated Videos will be used to illustrate the narration.
    3.  A concluding summary and a call to action (like, subscribe, comment).
    Ensure the narration is informative, engaging, and flows well.
    Break down complex information into digestible parts.
    Split the Narration into new lines if a new Video is needed.
    Do not include any video editing/music instructions or scene descriptions. Only pure Narration Text inside the square brackets with the Line Number, not titles but what needs to be narrated. Timings placed outside the square brackets.
    Enclose the Narrations like this:
    [LINE 1: Narration Text Here]
    [LINE 2: Narration Text Here]
    """
    video_script_raw = llm_generate(script_prompt, system_prompt="You are an expert documentary scriptwriter specializing in historical mysteries for a YouTube audience.", max_tokens=4000) # Increased max_tokens

    if not video_script_raw:
        print("Failed to generate video script. Exiting.")
        exit()

    # Extract Narration and place them in a list
    i = 1
    for line in video_script_raw.split('\n'):
        narration = extract_result(line, "LINE " + str(i))
        if narration:
            project.episode.narrations.append(narration.strip())
            i += 1

    with open(project.directories["scripts"] / "narration.txt", "w", encoding="utf-8") as f:
        for narration in project.episode.narrations:
            f.write(narration + "\n\n")


# --- 4. Storyboard Images ---
def create_img_prompts(project):
    i = 0
    if project.resume and (project.directories["scripts"] / "img_prompts.json").exists():
        with open(project.directories["scripts"] / "img_prompts.json", "r", encoding="utf-8") as f:
            existing_prompts = json.load(f)
            project.episode.img_prompts = existing_prompts
            i = existing_prompts[-1]["group"] + 1 if existing_prompts else 0
        if i >= len(project.episode.narrations):
            print("All image prompts already generated. Skipping.")
            return
        print(f"Resuming image prompt generation at index {i}.")
        

    print_stage("3.0 Generating Storyboard Images Prompts...")

    for i in tqdm(range(i, len(project.episode.narrations)), desc="Generating prompts", unit="narration"):
        #Get the corresponding Audio and extract the duration
        real_duration = float(mediainfo(project.episode.nar_audio[i])['duration'])
        duration_s = int(real_duration)

        # Create more descriptive prompt for image generation from visual description
        system_prompt = "You are an AI assistant that creates vivid image generation prompts from the narration that will be used for creating a youtube video."
        image_gen_prompt = f"Decide on the number of short animated scenes for the narration: '{project.episode.narrations[i]}'\n" \
        "The sum of duration of all scenes should not exceed {duration_s} seconds.\n" \
        "For each scene, create a detailed prompt for image generation, video generation and their respective timing" \
        "Format each output as.\n" \
        "[Image Prompt 1: detailed Prompt]\n" \
        "[Video Prompt 1: detailed Prompt]\n" \
        "[Duration 1: Scene Timing in seconds]"

        detailed_image_prompt = llm_generate(image_gen_prompt, system_prompt=system_prompt, temperature=0.5)

        if not detailed_image_prompt:
            print("Failed to generate Prompts. Exiting.")
            exit()

        # Extract each image and video prompts
        j = 1
        
        prompts = []
        image_prompt = video_prompt = duration = None
        for line in detailed_image_prompt.split('\n'):
            if extract_result(line, "Image Prompt " + str(j)):
                image_prompt = extract_result(line, "Image Prompt " + str(j))
            if extract_result(line, "Video Prompt " + str(j)):
                video_prompt = extract_result(line, "Video Prompt " + str(j))
            if extract_result(line, "Duration " + str(j)):
                duration = extract_result(line, "Duration " + str(j))

            if image_prompt and video_prompt and duration:
                prompts.append({
                    "image": image_prompt.strip(),
                    "video": video_prompt.strip(),
                    "duration": float(re.search(r'\d+(\.\d+)?', duration.strip()).group()),
                    "group": i
                })
                image_prompt = video_prompt = duration = None
                j += 1

        # Confirm each prompt has image, video, and duration
        if not all("image" in prompt and "video" in prompt and "duration" in prompt for prompt in prompts):
            print("Some prompts are missing image, video, or duration information. Exiting.")
            exit()

        # Adjust duration to ensure total time is exactly the same as the narration duration
        total_duration = sum(prompt["duration"] for prompt in prompts)
        for prompt in prompts:
            prompt["duration"] = prompt["duration"] * (real_duration / total_duration)

        # Save prompts to the img_prompts
        project.episode.img_prompts.extend(prompts)

        # Save prompts to json
        img_prompts_path = project.directories["scripts"] / "img_prompts.json"
        if img_prompts_path.exists():
            with open(img_prompts_path, "r", encoding="utf-8") as f:
                existing_prompts = json.load(f)
            existing_prompts += prompts
        else:
            existing_prompts = prompts

        with open(img_prompts_path, "w", encoding="utf-8") as f:
            json.dump(existing_prompts, f, indent=4)







        


