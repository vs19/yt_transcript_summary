import os
import re
import requests
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript
import openai
import logging

# Set up logging
logging.basicConfig(filename='transcript_summary.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Constants
YOUTUBE_API_KEY = 'YOUR_YOUTUBE_API_KEY'
OPENAI_API_KEY = 'YOUR_OPENAI_API_KEY'
TRANSCRIPTS_FOLDER = 'transcripts'
SUMMARIES_FOLDER = 'summaries'

# Initialize the OpenAI API
openai.api_key = OPENAI_API_KEY

# Function to get video IDs from a YouTube channel
def get_video_ids_from_channel(channel_id):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    video_ids = []
    
    request = youtube.search().list(
        part="id",
        channelId=channel_id,
        maxResults=50,
        type="video"
    )

    while request:
        response = request.execute()
        for item in response['items']:
            video_ids.append(item['id']['videoId'])
        request = youtube.search().list_next(request, response)

    return video_ids

# Function to retrieve and clean transcript
def get_clean_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        cleaned_transcript = ' '.join([text['text'] for text in transcript])
        return cleaned_transcript
    except CouldNotRetrieveTranscript:
        logging.error(f"Could not retrieve transcript for video ID {video_id}")
        return None

# Function to generate summary using OpenAI
def generate_summary(text):
    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=f"Summarize the following text:\n\n{text}",
            max_tokens=150
        )
        summary = response.choices[0].text.strip()
        return summary
    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        return None

# Function to save text to a file
def save_text_to_file(text, folder, filename):
    if not os.path.exists(folder):
        os.makedirs(folder)
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(text)

# Main function
def main(channel_url):
    # Extract channel ID from URL
    if '@' in channel_url:
        channel_id = get_channel_id_from_url(channel_url)
        if not channel_id:
            logging.error(f"Failed to get channel ID from URL: {channel_url}")
            return
    else:
        channel_id = channel_url.split('/')[-1]
    
    video_ids = get_video_ids_from_channel(channel_id)
    
    for video_id in video_ids:
        video_info = requests.get(f'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}').json()
        channel_name = video_info['items'][0]['snippet']['channelTitle']
        video_title = video_info['items'][0]['snippet']['title']
        filename = f"{channel_name} - {video_title}.txt"
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # Remove invalid characters from filename
        
        # Retrieve and save transcript
        transcript = get_clean_transcript(video_id)
        if transcript:
            save_text_to_file(transcript, TRANSCRIPTS_FOLDER, filename)
            
            # Generate and save summary
            summary = generate_summary(transcript)
            if summary:
                save_text_to_file(summary, SUMMARIES_FOLDER, filename)
                logging.info(f"Processed and saved transcript and summary for video ID {video_id}")
            else:
                logging.error(f"Failed to generate summary for video ID {video_id}")
        else:
            logging.error(f"Failed to retrieve transcript for video ID {video_id}")

def get_channel_id_from_url(channel_url):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    username = channel_url.split('@')[-1]
    try:
        request = youtube.channels().list(
            part="id",
            forUsername=username
        )
        response = request.execute()
        return response['items'][0]['id']
    except Exception as e:
        logging.error(f"Error fetching channel ID for username {username}: {e}")
        return None

if __name__ == "__main__":
    channel_url = input("Enter YouTube channel URL or ID: ")
    main(channel_url)
