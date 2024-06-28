import streamlit as st
from openai import OpenAI
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import re
import os

# Function to get the video transcript
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print(transcript)
        return transcript
    except Exception as e:
        st.error(f"Error fetching transcript: {e}")
        return None

# Function to analyze the transcript and suggest clips using OpenAI
def suggest_clips_with_openai(transcript, api_key, prompt, duration=10):
    # Combine transcript text into a single string
    # transcript_text = " ".join([entry['text'] for entry in transcript])

    # Format each entry to include text, start, and duration
    formatted_entries = [f"{entry['text']} (start: {entry['start']}, duration: {entry['duration']})" for entry in transcript]

    # Join the formatted entries into a single string with new lines
    transcript_text = '\n'.join(formatted_entries)
    
    # OpenAI API call for analysis
    client = OpenAI(api_key=api_key)

    # openai.api_key = api_key
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that helps suggest interesting clips from a YouTube video transcript."},
            {"role": "user", "content": prompt 
             + """
                Provide the start and end times for each clip in the following format:

                Clip 1:
                - Start time: ss
                - End time: ss
                - Transcript: "..."

                Clip 2:
                - Start time: ss
                - End time: ss
                - Transcript: "..."
             
               """
             + f" Transcript: {transcript_text}"}
        ],
    )

    # Extract suggested clips from the response
    suggested_clips = []
    # print (response.choices[0].message.content)
    
    suggested_clips = []
    content = response.choices[0].message.content.replace("**", "")
    
    # Regular expressions to match start and end times
    start_times = re.findall(r'Start time: ([\d.]+)', content)
    end_times = re.findall(r'End time: ([\d.]+)', content)

    # Convert the extracted times to floats
    start_times = [float(time) for time in start_times]
    end_times = [float(time) for time in end_times]

    # Combine start and end times into an array of tuples
    suggested_clips = list(zip(start_times, end_times))
    # Combine start and end times into tuples and append to the list
    # suggested_clips = [(start, end) for start, end in zip(start_times, end_times)]

    return suggested_clips

def mmss_to_seconds(mmss):
    minutes, seconds = map(int, mmss.split(':'))
    return minutes * 60 + seconds

# Function to download the video
def download_video(url, output_path):
    yt = YouTube(url)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
    stream.download(output_path=output_path)
    return stream.default_filename

# Function to delete files
def delete_files(path):
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            st.error(f"Error deleting file {file_path}: {e}")

# Default prompt
DEFAULT_PROMPT = """Analyze the YouTube video and suggest 2 segments for clips that mention "Hall of Science" 

Make sure the clips do not repeat and are only 10 seconds long."""
DEFAULT_PROMPT_OLD = """Analyze the following YouTube video transcript and suggest 2 segments for clips that mention "goofy." Make sure the clips do not repeat and are only 10 seconds long.

Provide the start and end times for each clip in the following format:

Clip 1:
- Start time: ss
- End time: ss
- Transcript: "..."

Clip 2:
- Start time: ss
- End time: ss
- Transcript: "..."
"""

# Streamlit app
st.title("YouTube Video Clip Suggester")

# User inputs
url = st.text_input("YouTube Video URL", key="url", value="https://www.youtube.com/watch?v=EorJ8cEzsZo")
api_key = st.text_input("OpenAI API Key", type="password", key="api_key")
download_path = st.text_input("Download Path", value="./", key="download_path")
user_prompt = st.text_area("User Prompt", value=DEFAULT_PROMPT, height=150, key="user_prompt")

# Initialize session state
if "reset" not in st.session_state:
    st.session_state.reset = False

if st.button("Suggest Clips"):
    if url and api_key and download_path:
        delete_files(download_path)
        with st.spinner('Fetching transcript and analyzing...'):
            video_id = re.search(r"v=([a-zA-Z0-9_-]+)", url).group(1)
            
            # Get the transcript
            transcript = get_transcript(video_id)
            if transcript:
                # Suggest clips using OpenAI
                suggested_clips = suggest_clips_with_openai(transcript, api_key, user_prompt)
                st.write("Suggested clips (start_time, end_time):")
                for clip in suggested_clips:
                    st.write(clip)

                # Download the video
                with st.spinner('Downloading video...'):
                    video_filename = download_video(url, download_path)
                    st.write(f"Downloaded video: {video_filename}")

                # Create clips from the suggested times
                clips = []
                with st.spinner('Creating clips...'):
                    for i, (start, end) in enumerate(suggested_clips):
                        clip_filename = f"{download_path}/clip_{i+1}.mp4"
                        ffmpeg_extract_subclip(f"{download_path}/{video_filename}", start, end, targetname=clip_filename)
                        clips.append(clip_filename)
                        st.write(f"Created clip: {clip_filename}")

                # Display the clips
                st.write("Generated Clips:")
                for clip in clips:
                    st.video(clip)
            else:
                st.error("Failed to get the transcript.")
    else:
        st.error("Please provide all required inputs.")

if st.button("Reset"):
    if download_path:
        with st.spinner('Deleting files...'):
            delete_files(download_path)
            st.success("All files deleted.")
            st.session_state.reset = True
    else:
        st.error("Please provide the download path.")

if st.session_state.reset:
    #st.text_area("User Prompt", value=DEFAULT_PROMPT, height=150, key="user_prompt")
    st.session_state.reset = False
    st.rerun() 
