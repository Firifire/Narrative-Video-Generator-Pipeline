import os
import subprocess
from project import *
from generate import *
from create_script import *
from create_video import *
from merge import *

def main():
    print_stage("Initializing YouTube Video Project...")

    project = Project(base="YT", args=parse_args())

    create_channel(project)
    project.start()

    create_title(project)
    create_script(project)
    create_voice(project)
    create_img_prompts(project)

    subprocess.run(LLM_UNLOAD_CMD)

    create_frames(project)
    create_video(project)
    combine(project)
    exit()


if __name__ == "__main__":
    if not check_required_workflows([TXT2IMG_WORKFLOW, IMG2VID_WORKFLOW]):
        exit("Required ComfyUI workflows are missing. Please ensure they exist in the specified paths.")
    
    main()