import re
from config import *
from generate import *

def create_frames(scenes_data, prompts_first):
    # --- 4. Storyboard Images ---
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