# Video Processing API - Documentation

## Overview

This API allows you to process video files by extracting frames, audio, and generating descriptive content based on the frames and audio using OpenAI. It is implemented using Flask, and makes use of external tools such as `ffmpeg` for processing video files.

## Features

- Extract frames from video at specified intervals.
- Extract audio from video.
- Generate descriptive content based on frames using OpenAI's GPT model.
- Clean up folders after processing to ensure minimal disk usage.

## Prerequisites

- Python 3.8 or higher
- Virtual Environment (`python3-venv`) for isolated package installation
- `ffmpeg` installed on your system
- An OpenAI API key (stored in an `.env` file)

## Installation

### Step 1: Clone the Repository

```sh
$ git clone https://github.com/ChornyiDev/Video-Framer.git
$ cd Video-Framer
```

### Step 2: Set Up a Virtual Environment

Create and activate a virtual environment:

```sh
$ python3 -m venv venv
$ source venv/bin/activate
```

### Step 3: Install Dependencies

Install the required Python packages:

```sh
$ pip install -r requirements.txt
```

### Step 4: Install ffmpeg

If `ffmpeg` is not installed, you can install it on Ubuntu using the following command:

```sh
$ sudo apt update
$ sudo apt install ffmpeg
```

### Step 5: Set Up Environment Variables

Create a `.env` file in the root of your project directory and add your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key
BASE_URL=http://your_host_url:5001
```

Replace `your_openai_api_key` with your actual OpenAI API key, and `your_base_url` with the host URL or domain of your server. This generates URLs for frames that OpenAI can access during the video description generation process.

## Running the Application

To start the Flask server, run:

```sh
$ python app.py
```

This will run the server at `http://0.0.0.0:5001` by default.

## Usage

### Endpoint: `/upload` (POST)

This endpoint accepts a video URL and processes it.

#### Parameters:

- `video_url` (string): The URL of the video file to be processed.
- `video_id` (string, optional): A unique identifier for the video. If not provided, defaults to 'video'.
- `system_prompt` (string, optional): A custom system prompt for generating video descriptions using OpenAI.
- `min_duration` (float, optional): Minimum video duration in seconds required for description generation. Default: 5 seconds.
- `min_words` (integer, optional): Minimum word count in transcription required for description generation. Default: 5 words.
- `max_frames` (integer, optional): Maximum number of frames to extract from the video. Default: 10 frames.

#### Frame Extraction Logic:

The API automatically determines frame extraction intervals based on video duration:
- Videos ≤30 seconds: 5-second interval
- Videos 31-60 seconds: 10-second interval
- Videos >60 seconds: 20-second interval

#### Example Request:

```sh
curl -X POST http://localhost:5001/upload \
-F "video_url=https://example.com/sample_video.mp4" \
-F "video_id=my_video" \
-F "min_duration=10" \
-F "min_words=10" \
-F "max_frames=8"
```

#### Example Responses:

Successful processing:
```json
{
  "status": "Processed successfully",
  "transcription": "Transcription of the audio",
  "description": "Description generated from video frames"
}
```

Duration limitation:
```json
{
  "status": "Processed with limitations",
  "description": "Video duration (3.5s) is less than minimum required duration (5s)",
  "transcription": "Transcription of the audio"
}
```

Word count limitation:
```json
{
  "status": "Processed with limitations",
  "description": "Transcription word count (3) is less than minimum required words (5)",
  "transcription": "Transcription of the audio"
}
```

### Endpoint: `/frames/<filename>` (GET)

The /frames/\<filename> endpoint allows OpenAI to access the frames when generating a video description.&#x20;

#### Example Request:

```sh
curl http://localhost:5001/frames/frame_0001.jpg
```

## Folder Structure

- `uploads/`: Stores uploaded video files.
- `frames/`: Stores frames extracted from videos.
- `audio/`: Stores audio extracted from videos.

## Error Handling

- `404 Not Found`: If a resource (frame or audio) is not found.
- `500 Internal Server Error`: If an unexpected error occurs during processing.

## Cleanup Process

After each video is processed, the `clear_folders()` function is automatically called to delete all files in `uploads/`, `frames/`, and `audio/` directories to minimize disk usage.

## Running the Application as a Service

To run this application as a service that starts on boot, you can create a `systemd` service file.

Example service file (`/etc/systemd/system/video_framer.service`):

```ini
[Unit]
Description=Video Framer Service
After=network.target

[Service]
User=root
WorkingDirectory=/path/to/Video-Framer
ExecStart=/path/to/Video-Framer/venv/bin/python /path/to/Video-Framer/app.py
Restart=always
EnvironmentFile=/path/to/Video-Framer/.env

[Install]
WantedBy=multi-user.target
```

After creating the service file:

```sh
$ sudo systemctl daemon-reload
$ sudo systemctl enable video_framer.service
$ sudo systemctl start video_framer.service
$ sudo systemctl status video_framer.service
```
