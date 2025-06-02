import os
import glob
import subprocess
from project import *

clip_pattern="clip_*.mp4"

def get_media_duration(file_path: Path) -> float | None:
    """
    Gets the duration of a media file in seconds using ffprobe.
    Returns duration as a float, or None if an error occurs.
    Assumes ffprobe is in PATH or its full path is configured similarly to FFMPEG_PATH.
    """
    # Determine ffprobe command, assuming it's in the same directory or PATH as ffmpeg
    ffprobe_executable = 'ffprobe'
    if 'FFMPEG_PATH' in globals() and Path(FFMPEG_PATH).name.lower() == 'ffmpeg.exe':
        ffprobe_executable = str(Path(FFMPEG_PATH).parent / 'ffprobe.exe')
    elif 'FFMPEG_PATH' in globals() and Path(FFMPEG_PATH).name.lower() == 'ffmpeg':
        ffprobe_executable = str(Path(FFMPEG_PATH).parent / 'ffprobe')
        if not Path(ffprobe_executable).exists(): # Fallback if not next to ffmpeg
             ffprobe_executable = 'ffprobe'

    ffprobe_cmd = [
        ffprobe_executable,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(file_path)
    ]
    try:
        process = subprocess.Popen(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=30) # Keep timeout for robustness

        if process.returncode == 0 and stdout:
            return float(stdout.decode().strip())
        else:
            # Simplified error reporting
            print(f"Error getting duration for '{file_path}' using ffprobe.")
            if stderr: # Still useful to print stderr if available
                 print(f"ffprobe stderr: {stderr.decode()}")
            return None
    except Exception as e:
        # General exception handler
        print(f"An unexpected error occurred while trying to get duration for '{file_path}': {e}")
        return None

def combine(project):
    input_folder = project.directories["video_clips"]
    output_filename = project.directories["final_video"].resolve() / "merged_video.mp4"
    original_cwd = os.getcwd()

    print_stage("Merging Video Clips...")

    try:
        os.chdir(input_folder)

        video_files = sorted(glob.glob(clip_pattern))

        if not video_files:
            exit(f"No video files found matching pattern '{clip_pattern}' in folder '{input_folder}'.")

        list_filename = "mylist.txt"
        with open(list_filename, 'w') as f:
            for video_file in video_files:
                f.write(f"file '{os.path.join(os.getcwd(), video_file)}'\n")

        ffmpeg_command = [
            FFMPEG_PATH,
            '-f', 'concat',
            '-safe', '0',
            '-i', list_filename,
            '-c', 'copy',
            '-y',
            str(output_filename)
        ]

        # Execute FFmpeg command
        try:
            process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                print(f"\nSuccessfully merged videos into '{os.path.join(os.getcwd(), output_filename)}'")
            else:
                print("\nError during FFmpeg execution:")
                print("Stdout:")
                print(stdout.decode())
                print("Stderr:")
                exit(stderr.decode())
        except FileNotFoundError:
            print("\nError: FFmpeg not found. Please ensure FFmpeg is installed and in your system's PATH.")
            return False
        except Exception as e:
            print(f"\nAn unexpected error occurred during FFmpeg execution: {e}")
            return False
        finally:
            if os.path.exists(list_filename):
                os.remove(list_filename)
                print(f"Cleaned up temporary file: {list_filename}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
    finally:
        os.chdir(original_cwd)

    vid_duration = get_media_duration(output_filename)

    aud_duration = 0
    for audio in project.episode.nar_audio:
        aud_duration += get_media_duration(audio)

    silence = (max(0, vid_duration - aud_duration) * 1000 ) / len(project.episode.nar_audio)

    audio_path = merge_audio_files(project.episode.nar_audio, silence_duration=silence)
    output_path = project.directories["final_video"] / ("narration" + audio_path.suffix)
    if output_path.exists():
        output_path.unlink()
    audio_path.rename(output_path)

    # Final merge of video and audio
    final_output = project.directories["final_video"] / "final_video.mp4"
    ffmpeg_command = [
        FFMPEG_PATH,
        '-i', str(output_filename),
        '-i', str(output_path),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-y',
        str(final_output)
    ]
    
    try:
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print(f"\nSuccessfully created final video with audio: '{final_output}'")
        else:
            print("\nError during final FFmpeg execution:")
            print("Stdout:")
            print(stdout.decode())
            print("Stderr:")
            exit(stderr.decode())
    except FileNotFoundError:
        print("\nError: FFmpeg not found. Please ensure FFmpeg is installed and in your system's PATH.")
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred during final FFmpeg execution: {e}")
        return False
    
    print_stage("Video Clips Merged Successfully")
