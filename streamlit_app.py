import streamlit as st
import os
import cv2
import tempfile
from main import load_json, load_prompt, translate_to_ASL, concatenate_videos, GLOSS_VIDEO_JSON, PROMPT_FILE,OUTPUT_VIDEO

st.set_page_config(page_title="Sign Language Video Generator", layout="centered")
st.title("Sign Language Video Generator")
st.markdown("""
Enter an English sentence below. The app will translate it to sign language and generate a video using the available sign language clips.
""")

input_text = st.text_area("Enter English sentence:", "The data available from these pages can be used for research and education purposes, but cannot be redistributed without permission.")

if st.button("Translate and Generate Video"):
    with st.spinner("Translating and generating video..."):
        word_to_video = load_json(GLOSS_VIDEO_JSON)
        system_prompt = load_prompt(PROMPT_FILE)
        translation = translate_to_ASL(input_text, word_to_video, system_prompt)
        if not translation:
             st.error("Translation failed.")
        else: 
            video_ids = [word_to_video[word] for word in translation.split(" ")]
            output_video = concatenate_videos(video_ids)
            st.success("Video generated successfully!")
            st.video(output_video)
            st.info(translation)
        
