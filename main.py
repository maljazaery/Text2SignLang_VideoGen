import os
import base64
import json
import re
import cv2
import numpy as np
from openai import AzureOpenAI

# ================== CONFIGURATION ==================
VIDEO_DIR = os.path.join(
    "./sign_clips/"
)
GLOSS_VIDEO_JSON = "./gloss_video.json"
PROMPT_FILE = "./prompt"
OUTPUT_VIDEO = "output.mp4"

# Azure OpenAI settings
ENDPOINT_URL = os.getenv("ENDPOINT_URL", "https://ai-maljazaery-5364.cognitiveservices.azure.com/")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")
AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY",
    "****************"  # Replace with your actual API key,
)

# ================== UTILITY FUNCTIONS ==================
def load_json(filepath):
    """Load a JSON file and return its content."""
    with open(filepath, "r") as f:
        return json.load(f)

def load_prompt(filepath):
    """Load the system prompt from a file."""
    with open(filepath, "r") as f:
        return f.read()

def initialize_openai_client():
    """Initialize and return the Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=ENDPOINT_URL,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-05-01-preview",
    )

# ================== Azure OPENAI INTERACTION ==================
def get_model_response(system_prompt, user_input, first_attempt="", bad_outputs=""):
    """Send a prompt to the OpenAI model and return the generated text."""
    client = initialize_openai_client()
    chat_prompt = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "text", "text": user_input}]},
    ]
    if first_attempt and bad_outputs:
        chat_prompt.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"The first generate attempt was: {first_attempt} and the output has these words from outside dictionary: {bad_outputs}. Please try again.",
                    }
                ],
            }
        )
    completion = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=chat_prompt,
        max_tokens=800,
        temperature=0,
        top_p=0,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False,
    )
    output_text = completion.choices[0].message.content
    final_result_pattern = re.compile(r'<final_result>(.*?)</final_result>', re.DOTALL)
    match = final_result_pattern.search(output_text)
    if not match:
        print("No <final_result> tag found in the output text.")
        return ""
    final_result = match.group(1).strip().lower()
    return final_result

# ================== VIDEO ID EXTRACTION ==================
def find_words_outside_dictionary(text, word_to_video):
    """Extract video IDs from the model output using the dictionary."""
    outputs=[]
    bad_outputs = []
    for word in text.split(" "):
        if not word.strip():
            continue
        if word in word_to_video:
            outputs.append(word)
        else:
            bad_outputs.append(word)
    return ",".join(bad_outputs)

def translate_to_ASL(input_text, word_to_video, system_prompt):
    """Get video IDs for a given input text, retrying if output is bad."""
    output_text = get_model_response(system_prompt, input_text)
    bad_outputs = find_words_outside_dictionary(output_text, word_to_video)
    print(f"Initial output: {output_text}")
    
    trials = 0
    while bad_outputs:
        
        print(f"Retrying due to bad output: {bad_outputs}")
        output_text = get_model_response(system_prompt, input_text, first_attempt=output_text, bad_outputs=bad_outputs)
        print(f"Retry output: {output_text}")
        bad_outputs = find_words_outside_dictionary(output_text, word_to_video)
        
        trials+=1
        if trials>3:
            print("Too many retries, exiting.")
            return None
    
    return output_text

# ================== VIDEO PROCESSING ==================
def concatenate_videos(video_ids, output_path=OUTPUT_VIDEO):
    """Concatenate video files by IDs into a single video using OpenCV."""
    video_files = [os.path.join(VIDEO_DIR, f"{int(vid):05d}.mp4") for vid in video_ids]
    # Check if all video files exist
    for video in video_files:
        if not os.path.exists(video):
            print(f"File not found: {video}")
            return None
    
    from moviepy import VideoFileClip, concatenate_videoclips
    clips = [VideoFileClip(f) for f in video_files]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_path, codec='libx264', audio=False)
    
    return output_path

def play_video(video_path):
    """Play a video file using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow('Video', frame)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# ================== MAIN EXECUTION ==================
def main():
    word_to_video = load_json(GLOSS_VIDEO_JSON)
    system_prompt = load_prompt(PROMPT_FILE)
    # Example input (replace with your own)
    #input_text="8 cities around the world that offer both a low cost of living and a high quality of life"
    #input_text="What is the weather like today?"
    input_text="The following table contains a extended list of existing datasets including a variety of different sign languages and data content."
    #input_text="The data available from these pages can be used for research and education purposes, but cannot be redistributed without permission."

    translation = translate_to_ASL(input_text, word_to_video, system_prompt)
    if not translation:
        print("Translation failed.")
        return
    video_ids = [word_to_video[word] for word in translation.split(" ")]
    output_video = concatenate_videos(video_ids)
    if output_video:
        play_video(output_video)

if __name__ == "__main__":
    main()
