from config import *
import shutil

class Project:
    resume = False
    project_name = None
    niche = None

    def __init__(self, base, args):
        self.base = Path(base)
        self.create_new = args.create
        self.episode = Episode()
        if args.resume:
            self.project_name = args.resume
            self.resume = True
        elif args.new:
            self.project_name = args.new

    def video_project(self, episode):
        project_dir = self.base / self.project_name
        episode = project_dir / episode
        self.directories = {
            "project": project_dir,
            "workspace": project_dir / "workspace",  
            "episode": episode,
            "scripts": episode / "scripts",
            "storyboard": episode / "storyboard",
            "video_clips": episode / "video_clips",
            "audio": episode / "audio",
            "narration": episode / "audio" / "narration",
            "sfx": episode / "audio" / "sfx",
            "final_video": episode / "final_video",
        }
        
        self.create_directories()

    def start(self):
        project_dir = self.base / self.project_name
        new_episode_number = 0
        # Find the last episode number
        for episode in project_dir.iterdir():
            if episode.is_dir() and episode.name.isdigit():
                episode_number = int(episode.name)
                if episode_number > new_episode_number:
                    new_episode_number = episode_number
        if not self.resume:
            new_episode_number += 1
            print(f"Creating new episode: {new_episode_number:04d} of {project_dir.name}")
        else:
            if not (project_dir / f"{new_episode_number:04d}").exists():
                exit(f"No Episodes exists. Cannot resume.")
            print(f"Resuming episode: {new_episode_number:04d} of {project_dir.name}")
        self.video_project(f"{new_episode_number:04d}")
    
    def create_directories(self):
        """Creates necessary project directories."""
        for dir_path in self.directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
        # ComfyUI input dir might be cleared or managed per run
        if COMFYUI_INPUT_DIR.exists():
            for item in COMFYUI_INPUT_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
        COMFYUI_INPUT_DIR.mkdir(exist_ok=True) # Ensure it exists

class Episode:
    def __init__(self):
        self.name = ""
        self.concept = ""
        self.narrations = []
        self.nar_audio = []

        self.img_prompts = []

