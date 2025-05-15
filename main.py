import os
import json
import subprocess
import shutil
from pathlib import Path
from config import *
from generate import *
from create_script import *
from create_video import *


def get_word_timestamps_from_audio(narration_audio_path, narration_text):
    """Uses Whisper (via stable-ts) to get word-level timestamps."""
    try:
        import stable_whisper
        model = stable_whisper.load_model('base') # Or other sizes like 'small', 'medium'
        result = model.align(narration_audio_path, narration_text, language='en') # Assuming English
        
        timestamps = []
        for segment in result.segments:
            for word_info in segment.words:
                timestamps.append({
                    "word": word_info.word,
                    "start": word_info.start,
                    "end": word_info.end
                })
        print(f"Generated timestamps for {Path(narration_audio_path).name}")
        return timestamps
    except ImportError:
        print("stable-ts library not found. Please install it: pip install -U stable-ts")
        return []
    except Exception as e:
        print(f"Timestamp generation failed for {Path(narration_audio_path).name}: {e}")
        return []

def assemble_final_video(video_clips_paths, narration_segments, sfx_items, output_video_path):
    """Assembles the final video using FFmpeg."""
    if not video_clips_paths:
        print("No video clips provided for assembly.")
        return

    # Create a file list for FFmpeg concat demuxer
    concat_file_list = WORKSPACE_DIR / "ffmpeg_concat_list.txt"
    with open(concat_file_list, "w") as f:
        for clip_path in video_clips_paths:
            f.write(f"file '{Path(clip_path).resolve()}'\n")

    inputs = [f"-f", "concat", "-safe", "0", "-i", str(concat_file_list)]
    audio_maps = []
    filter_complex_parts = []
    
    current_video_duration = 0
    video_durations = []
    for i, clip_path in enumerate(video_clips_paths):
        try:
            result = subprocess.run([FFMPEG_PATH, '-i', str(Path(clip_path).resolve()), '-hide_banner'], capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            # FFmpeg outputs duration info to stderr
            duration_line = [line for line in e.stderr.split('\n') if "Duration:" in line]
            if duration_line:
                parts = duration_line[0].split(",")[0].split("Duration: ")[1].split(":")
                duration = int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
                video_durations.append(duration)
            else:
                print(f"Warning: Could not get duration for {clip_path}. Assuming 0.")
                video_durations.append(0) # Default or handle error
        else: # Should not happen if only duration is needed, but good for general check
             print(f"Warning: Could not get duration for {clip_path} via error parsing. Assuming 0.")
             video_durations.append(0)


    # Narration
    narration_offset = 0
    for i, segment in enumerate(narration_segments):
        audio_path = segment["audio_path"]
        start_time = segment["start_time"] # Absolute start time in the final video
        inputs.extend(["-i", str(Path(audio_path).resolve())])
        audio_stream_index = len(video_clips_paths) + i # base inputs + previous narrations
        
        # We need to map this audio to start at `start_time`
        # For simplicity, we'll map all narration to one track and handle offsets later if needed,
        # or assume TTS generates segments that are stitched together sequentially by FFmpeg.
        # A more robust way is to create silent audio of correct length and overlay.
        # Here, we assume narration audio files are for sequential parts of the script.
        # We'll use amix or complex filter graph later. For now, just add as inputs.
        # This example assumes a single continuous narration track made of segments.
        # If segments are separate and timed, a complex filter_complex is needed.

        # Simplified: Assume narration_audio_path is one continuous track for now.
        # This part needs significant improvement if narration is segmented and timed.
        # For now, we'll map the first narration track if it exists.
        if i == 0 and audio_path: # Placeholder for a single main narration track
            audio_maps.append(f"-map {len(inputs)-2}:a") # Map the last added audio input

    # SFX
    sfx_input_count = 0
    for i, sfx in enumerate(sfx_items):
        audio_path = sfx["audio_path"]
        start_time = sfx["start_time"] # Absolute start time
        sfx_input_index = len(inputs) # Current count before adding this SFX
        inputs.extend(["-i", str(Path(audio_path).resolve())])
        
        # Example of delaying SFX: [sfx_input_index:a]adelay=START_MS[sfx_delayed_i];
        # Then mix [sfx_delayed_i] with main audio.
        # This gets very complex quickly with many SFX.
        # For now, just adding them as inputs, manual mixing/timing in FFmpeg is hard this way.
        # A better approach: create a single mixed audio track first, then add to video.
        # Or use a complex filter_complex.
        # This part is a placeholder for a more robust SFX mixing strategy.
        if audio_path: # Map first SFX for now
             if not audio_maps: # If no narration, SFX is first audio
                  audio_maps.append(f"-map {sfx_input_index}:a")
             sfx_input_count +=1


    command = [FFMPEG_PATH] + inputs
    command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])
    
    if audio_maps: # If we have any audio to map
        command.extend(audio_maps)
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    else: # No audio, just copy video
        command.extend(["-an"]) # No audio

    command.extend(["-vf", f"scale={FINAL_VIDEO_WIDTH}:{FINAL_VIDEO_HEIGHT},fps={FINAL_VIDEO_FPS}", "-y", str(output_video_path)])
    
    # This is a VERY basic assembly. True synchronization of many narration parts and SFX
    # requires a much more sophisticated filter_complex graph.
    # Example:
    # ffmpeg -i clip1.mp4 -i clip2.mp4 -i narration1.wav -i sfx1.wav -filter_complex \
    # "[0:v][1:v]concat=n=2:v=1:a=0[vout]; \
    #  [2:a]adelay=1000|1000[narr1]; \
    #  [3:a]adelay=5000|5000[sfx_1]; \
    #  [narr1][sfx_1]amix=inputs=2[aout]" \
    # -map "[vout]" -map "[aout]" output.mp4
    # This script does NOT build such a complex graph dynamically yet.

    print(f"FFmpeg command: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Final video assembled at {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg video assembly failed: {e.stderr}")
    except Exception as e:
        print(f"FFmpeg video assembly failed: {e}")


def main():
    setup_directories()

    create_channel()
    create_title()
    scenes_data = create_script()
    prompts_first = create_img_prompts(scenes_data)

    subprocess.run(LLM_UNLOAD_CMD)

    create_frames(scenes_data, prompts_first)


    # --- 5. Video Clips (LTX-Video via ComfyUI) ---
    print_stage("5. Generating Video Clips...")
    # This requires a ComfyUI LTX-Video workflow, e.g., image-to-video.
    # Assume 'comfyui_workflows/ltx_img2vid_api.json'
    comfy_video_workflow_path = Path("comfyui_workflows/ltx_img2vid_api.json") # Relative

    if not comfy_video_workflow_path.exists():
        print(f"ComfyUI LTX-Video workflow not found at {comfy_video_workflow_path}. Skipping video clip generation.")
    else:
        generated_video_clip_paths = []
        for i, scene in enumerate(scenes_data):
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


    # --- 6. Voice-over (TTS) & Timestamping ---
    print_stage("6. Generating Narration Audio & Timestamps...")
    narration_segments_for_assembly = []
    full_narration_text = ""
    narration_audio_files = []

    for i, scene in enumerate(scenes_data):
        if scene["narration"]:
            narration_text = scene["narration"]
            full_narration_text += narration_text + " " # For full transcript later
            audio_filename = f"scene_{i+1}_narration.wav"
            narration_audio_path = generate_tts_audio(narration_text, audio_filename)
            if narration_audio_path:
                scene["narration_audio_path"] = narration_audio_path
                narration_audio_files.append(narration_audio_path)
                # For simplicity, we'll timestamp the whole narration later.
                # A more granular approach would timestamp per scene narration.
            else:
                print(f"Failed to generate narration for scene {i+1}")
    
    # Combine all narration audios into one for easier ASR timestamping
    # Or, if you prefer per-scene timing, call get_word_timestamps_from_audio for each scene["narration_audio_path"]
    # and scene["narration"]. This script simplifies to one global narration track for now.
    
    main_narration_output_path = NARRATION_DIR / "full_narration_combined.wav"
    if len(narration_audio_files) > 1:
        concat_narration_list = WORKSPACE_DIR / "ffmpeg_narration_concat_list.txt"
        with open(concat_narration_list, "w") as f:
            for audio_f in narration_audio_files:
                f.write(f"file '{Path(audio_f).resolve()}'\n")
        
        ffmpeg_concat_audio_cmd = [
            FFMPEG_PATH, "-f", "concat", "-safe", "0", "-i", str(concat_narration_list),
            "-c", "copy", "-y", str(main_narration_output_path)
        ]
        try:
            subprocess.run(ffmpeg_concat_audio_cmd, check=True, capture_output=True)
            print(f"Combined narration saved to {main_narration_output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to combine narration tracks: {e.stderr.decode()}")
            main_narration_output_path = None # Failed
    elif len(narration_audio_files) == 1:
        shutil.copy(narration_audio_files[0], main_narration_output_path)
        print(f"Narration (single file) copied to {main_narration_output_path}")
    else:
        main_narration_output_path = None
        print("No narration audio generated.")

    timed_narration_script = []
    if main_narration_output_path and Path(main_narration_output_path).exists() and full_narration_text.strip():
        print("Attempting to get timestamps for the full narration...")
        timed_narration_script = get_word_timestamps_from_audio(str(main_narration_output_path), full_narration_text.strip())
        if timed_narration_script:
            with open(SCRIPTS_DIR / "07_timed_narration_script.json", "w", encoding="utf-8") as f:
                json.dump(timed_narration_script, f, indent=4)
            print(f"Timed narration script saved.")
            # For assembly, we'd use the main_narration_output_path and assume it starts at 0.
            # If per-scene timing was done, logic here would be different.
            narration_segments_for_assembly.append({
                "audio_path": str(main_narration_output_path),
                "start_time": 0 # Assuming starts at the beginning
            })
        else:
            print("Failed to get timestamps. Narration will not be timed for assembly.")
            # Still add the untimed audio if it exists
            narration_segments_for_assembly.append({
                "audio_path": str(main_narration_output_path),
                "start_time": 0
            })
    
    with open(SCRIPTS_DIR / "08_scenes_with_narration_audio.json", "w", encoding="utf-8") as f:
        json.dump(scenes_data, f, indent=4)


    # # --- 7. Sound Effects ---
    # print_stage("7. Generating Sound Effects...")
    # sfx_items_for_assembly = []
    # # This part requires knowing WHEN each SFX should play.
    # # The simple script parser above just lists cues per scene.
    # # A more advanced system would:
    # #   1. Have the LLM output SFX cues with approximate timing within the scene's narration.
    # #   2. Use the word timestamps from narration to calculate absolute SFX start times.
    # # For this script, we'll generate SFX but not accurately time them for assembly without more info.
    
    # sfx_time_offset_within_scene = 0 # Placeholder
    # for i, scene in enumerate(scenes_data):
    #     scene_start_time_in_video = sum(video_durations[:i]) # Approximate scene start

    #     for cue_index, sfx_cue in enumerate(scene.get("sfx_cues", [])):
    #         if sfx_cue: # Ensure cue is not empty
    #             sfx_filename = f"scene_{i+1}_sfx_{cue_index}_{sfx_cue.replace(' ','_')[:20]}.wav" # Sanitize
    #             sfx_audio_path = generate_sfx_audio(sfx_cue, sfx_filename)
    #             if sfx_audio_path:
    #                 scene.setdefault("sfx_audio_paths", []).append(sfx_audio_path)
    #                 # Placeholder timing: SFX starts a bit into the scene, or after previous SFX in same scene
    #                 # THIS IS A MAJOR SIMPLIFICATION. Real timing needs to come from script or ASR alignment.
    #                 approx_sfx_start_time = scene_start_time_in_video + sfx_time_offset_within_scene
    #                 sfx_items_for_assembly.append({
    #                     "audio_path": sfx_audio_path,
    #                     "start_time": approx_sfx_start_time # Needs to be absolute time in final video
    #                 })
    #                 sfx_time_offset_within_scene += 3 # Assume SFX are ~3s and play sequentially for now
    #     sfx_time_offset_within_scene = 0 # Reset for next scene

    # with open(SCRIPTS_DIR / "09_scenes_with_sfx_audio.json", "w", encoding="utf-8") as f:
    #     json.dump(scenes_data, f, indent=4)


    # --- 8. Assembly (Video Editing) ---
    print_stage("8. Assembling Final Video...")
    final_video_filename = f"{chosen_channel_name.replace(' ','_')}_{chosen_video_title.replace(' ','_')[:30]}.mp4"
    final_output_path = FINAL_VIDEO_DIR / final_video_filename

    # Reload video clip paths if they were generated
    video_clips_for_assembly = []
    if (SCRIPTS_DIR / "06_scenes_with_videos.json").exists():
        with open(SCRIPTS_DIR / "06_scenes_with_videos.json", "r", encoding="utf-8") as f:
            scenes_data_with_videos = json.load(f)
        for scene in scenes_data_with_videos:
            if scene.get("video_clip_path") and Path(scene["video_clip_path"]).exists():
                video_clips_for_assembly.append(scene["video_clip_path"])
    
    if not video_clips_for_assembly:
        print("No video clips found to assemble. Exiting assembly.")
        return

    assemble_final_video(video_clips_for_assembly, narration_segments_for_assembly, sfx_items_for_assembly, final_output_path)

    print_stage("Pipeline Finished.")


if __name__ == "__main__":
    # --- Pre-flight checks for ComfyUI workflow files ---
    # User needs to create these JSON API workflow files from their ComfyUI setup.
    # This script refers to them but doesn't create them.
    required_comfy_workflows = [
        "comfyui_workflows/yt_txt3img.json",
        "comfyui_workflows/ltx_img2vid_api.json"
    ]
    missing_workflows = False
    for wf_path_str in required_comfy_workflows:
        wf_path = Path(wf_path_str)
        if not wf_path.exists():
            print(f"CRITICAL ERROR: ComfyUI workflow file not found: {wf_path.resolve()}")
            print("Please create this API workflow JSON in ComfyUI and save it to the specified path.")
            missing_workflows = True
    if missing_workflows:
        print("Exiting due to missing ComfyUI workflow files.")
    else:
        main()