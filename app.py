# Import necessary modules
from flask import Flask, request, jsonify, send_from_directory, url_for
import os
import subprocess
import shutil
import requests
from dotenv import load_dotenv
from openai import OpenAI  # Ensure you are using the correct OpenAI client

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Set up paths for saving videos, frames, and audio
UPLOAD_FOLDER = 'uploads'
FRAMES_FOLDER = 'frames'
AUDIO_FOLDER = 'audio'

# Create directories for saving videos, frames, and audio
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FRAMES_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Get the base URL from the environment variable or set a default value
BASE_URL = os.environ.get('BASE_URL').rstrip('/')

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))  # Ensure you have set OPENAI_API_KEY

# Function to extract frames and audio from video
def extract_frames_and_audio(video_path, video_id, interval=2, max_frames=100):
    # Extract frames
    output_pattern = os.path.join(FRAMES_FOLDER, 'frame_%04d.jpg') if video_id == 'video' else os.path.join(FRAMES_FOLDER, f'{video_id}_frame_%04d.jpg')  # Save frames in JPEG format for smaller size
    frame_command = [
        'ffmpeg', '-i', video_path, '-vf', f'fps=1/{interval}', '-q:v', '9', output_pattern  # Use -q:v to set quality
    ]
    try:
        subprocess.run(frame_command, check=True)
    except subprocess.CalledProcessError:
        return None

    # Limit the number of frames
    frame_files = sorted([frame for frame in os.listdir(FRAMES_FOLDER) if (frame.startswith('frame_') if video_id == 'video' else frame.startswith(f'{video_id}_frame_')) and frame.endswith('.jpg')])
    if len(frame_files) > max_frames:
        for frame in frame_files[max_frames:]:
            os.remove(os.path.join(FRAMES_FOLDER, frame))

    # Extract audio
    audio_output = os.path.join(AUDIO_FOLDER, 'audio.mp3') if video_id == 'video' else os.path.join(AUDIO_FOLDER, f'{video_id}.mp3')  
    audio_command = ['ffmpeg', '-i', video_path, '-c:a', 'libmp3lame', '-b:a', '64k', audio_output]

    try:
        subprocess.run(audio_command, check=True)
    except subprocess.CalledProcessError:
        return None

    return audio_output

# Function to get video description using OpenAI
def describe_video(frames_folder, audio_path, video_id, system_prompt=None):
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))  # Ensure you have set OPENAI_API_KEY
    
    # Get audio transcription
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            transcription_text = transcription.text
    except Exception as e:
        print(f"Audio transcription error: {e}")
        return {"error": "Audio transcription failed", "details": str(e)}

    # Get frame URLs using BASE_URL
    frame_urls = []
    for frame in sorted(os.listdir(frames_folder)):
        if frame.startswith(f'{video_id}_frame_') and frame.endswith('.jpg'):
            frame_url = f"{BASE_URL}/frames/{frame}"
            frame_urls.append(frame_url)
    
    # Use system prompt or default prompt
    if not system_prompt:
        system_prompt = "As a video Assistant, your goal is to describe a video with a focus on context that will be useful for bloggers, noting details that can be used as ideas for content: Plot, Key points, Atmosphere, Style, Visual look, Gestures, or anything else that could attract attention.\n\nAlso describe what exactly is happening in the video: The place depicted, the actions performed by people or objects, their interaction."

    # Create a request to OpenAI for video description
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": frame_url,
                        "detail": "low"
                    }
                } for frame_url in frame_urls
            ]
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure you are using the correct model
            messages=messages,
            max_tokens=2048
        )
        description = response.choices[0].message.content
        return {"description": description, "transcription": transcription_text}
    except Exception as e:
        print(f"Video description error: {e}")
        return {"error": "Video description failed", "details": str(e)}

# Function to clear folders after processing
def clear_folders():
    for folder in [UPLOAD_FOLDER, FRAMES_FOLDER, AUDIO_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

# Route to receive video URL
@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        # Get video URL and other parameters
        video_url = request.form.get('video_url')
        video_id = request.form.get('video_id') or 'video'
        frame_interval = request.form.get('frame_interval', type=int, default=2)
        system_prompt = request.form.get('system_prompt')
        
        if not video_url or not video_id:
            return jsonify({'error': 'Video URL or video_id not provided'}), 400

        # Download video from URL
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        # Save video with the name corresponding to video_id
        video_path = os.path.join(UPLOAD_FOLDER, 'video.mp4') if video_id == 'video' else os.path.join(UPLOAD_FOLDER, f'{video_id}.mp4')
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Extract frames and audio from video
        audio_path = extract_frames_and_audio(video_path, video_id, interval=frame_interval, max_frames=100)
        if not audio_path:
            return jsonify({'error': 'Failed to process video'}), 500

        # Get video description using OpenAI
        description_result = describe_video(FRAMES_FOLDER, audio_path, video_id, system_prompt)
        if 'error' in description_result:
            return jsonify(description_result), 500

        response = {
            'status': 'Processed successfully',
            'transcription': description_result['transcription'],
            'description': description_result['description']
        }
    finally:
        # Clear folders after script execution, regardless of the result
        clear_folders()

    return jsonify(response)

# Route to serve frames
@app.route('/frames/<filename>')
def serve_frame(filename):
    return send_from_directory(FRAMES_FOLDER, filename)

# Error handling for 404 errors
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

# Error handling for 500 errors
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Run the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
