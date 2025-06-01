import re
import shutil
from pathlib import Path
from pydub import AudioSegment

DEBUG = False

def check_required_workflows(required_workflows):
    """Check if all required workflows exist."""
    for wf_path_str in required_workflows:
        wf_path = Path(wf_path_str)
        if not wf_path.exists():
            return False
    return True

def print_stage(title):
    print("\n" + "="*10 + f" {title} " + "="*10)

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Start a new project or resume an existing one.")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--new', type=str, metavar='PROJECT_NAME', help='Start a new project with the given name')
    group.add_argument('--resume', type=str, metavar='PROJECT_NAME', help='Resume an existing project by name')
    group.add_argument('--create', action='store_true', help='Create a New Channel')

    return parser.parse_args()

def clean_text(text):
    return text.replace('*', '')

def extract_result(text, target_type):
    pattern = re.compile(r'\[([^\]:]+):\s*([^\]]+)\]')
    matches = pattern.findall(text)
    filtered = [content for t, content in matches if t == target_type]
    return clean_text(filtered[-1]) if filtered else None

def clean_workspace(project):
    workspace_path = project.directories["workspace"]
    if workspace_path.exists():
        for item in workspace_path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

def merge_audio_files(audio_files):
    """Merge multiple audio files into one."""
    if not audio_files:
        return
    
    combined = AudioSegment.empty()
    
    for audio_file in audio_files:
        segment = AudioSegment.from_file(audio_file)
        combined += segment

    output_path = audio_files[0].parent / ("merged_audio" + audio_files[0].suffix)
    combined.export(output_path, format=output_path.suffix[1:]) 

    return output_path

def debug_print(*args, **kwargs):
    """Print debug information if DEBUG is enabled."""
    if DEBUG:
        print(*args, **kwargs)