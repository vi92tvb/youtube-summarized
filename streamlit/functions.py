import os 
import re
import openai
import streamlit as st
from dotenv import load_dotenv

from pytube.exceptions import VideoUnavailable
from urllib.parse import urlparse, parse_qs
from moviepy.editor import *
from pytube import YouTube

from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import TextLoader
from langchain.docstore.document import Document
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline
from googletrans import Translator
from googleapiclient.discovery import build
from gtts import gTTS
import tempfile

load_dotenv()

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
OPENAI_KEY = os.environ.get('OPENAI_KEY')

def is_valid_youtube_url(url: str) -> bool:
    # Check if the URL is a valid YouTube video URL
    try:
        # Create a YouTube object
        yt = YouTube(url)

        # Check if the video is available
        if not yt.video_id:
            return False

    except (VideoUnavailable, Exception):
        return False

    # Return True if the video is available
    return yt.streams.filter(adaptive=True).first() is not None

# Calculate YouTube video duration
def get_video_duration(url: str) -> float:
    yt = YouTube(url)  
    video_length = round(yt.length / 60, 2)

    return video_length

# Get Video Thumbnail URL & Title
def video_info(url: str):

    yt = YouTube(url)

    # Get the thumbnail URL and title
    thumbnail_url = yt.thumbnail_url
    title = yt.title

    return thumbnail_url, title

def get_video_information(yt_key, video_id):
    youtube = build('youtube', 'v3', developerKey=yt_key)

    request = youtube.videos().list(
        part="snippet",
        id=video_id
    )

    response = request.execute()

    video_data = response.get('items', [])[0]

    title = video_data['snippet']['title']
    description = video_data['snippet']['description']
    author = video_data['snippet']['channelTitle']

    return author, title, description

def parse_text_info(input_list):
    #regex to remove timestamps and speaker names
    pattern = re.compile(r"'text':\s+'(?:\[[^\]]*\]\s*)?([^']*)'")
    output = ""
    for item in input_list:
        match = pattern.search(str(item))
        if match:
            text = match.group(1).strip()
            text = text.replace('\n', ' ')
            text = re.sub(' +', ' ', text)
            output += text + " "
       
    return output.strip()

# Download YouTube video as Audio
def download_audio(url: str):

    yt = YouTube(url)

    # Extract the video_id from the url
    query = urlparse(url).query
    params = parse_qs(query)
    video_id = params["v"][0]

    # Get the first available audio stream and download it
    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_stream.download(output_path="tmp/")

    # Convert the downloaded audio file to mp3 format
    audio_path = os.path.join("tmp/", audio_stream.default_filename)
    audio_clip = AudioFileClip(audio_path)
    audio_clip.write_audiofile(os.path.join("tmp/", f"{video_id}.mp3"))

    # Delete the original audio stream
    os.remove(audio_path)

# Transcription 
def transcribe_audio(file_path, video_id):
    # The path of the transcript
    transcript_filepath = f"tmp/{video_id}.txt"

    # Get the size of the file in bytes
    file_size = os.path.getsize(file_path)

    # Convert bytes to megabytes
    file_size_in_mb = file_size / (1024 * 1024)

    # Check if the file size is less than 25 MB
    if file_size_in_mb < 25:
        with open(file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            
            # Writing the content of transcript into a txt file
            with open(transcript_filepath, 'w') as transcript_file:
                transcript_file.write(transcript['text'])

        # Deleting the mp3 file
        os.remove(file_path)

    else:
        print("Please provide a smaller audio file (less than 25mb).")

# Transcription 
def transcribe_youtube(video_id):
    transcript_filepath = f"tmp/{video_id}.txt"
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        for transcript in transcript_list:
            captions = transcript.fetch()
            with open(transcript_filepath, 'w') as transcript_file:
                transcript_file.write(parse_text_info(captions))
    except:
        captions = None

# Translate
def translateToVietnamese(text):
    translator = Translator()
    try:
        translation = translator.translate(text, dest='vi')
        vietnamese_text = translation.text
    except Exception as e:
        vietnamese_text = "Translation failed"

    return vietnamese_text

# Function to generate summary using OpenAI API
def generateSummaryWithCaptions(captions, summary_length, yt_url, yt_title, yt_description, yt_author):
    # Set default length to 200 tokens
    # Set summary length to default value if user does not select a summary length
    try:
        if summary_length >= 300:
            message = f"Vui lòng cung cấp bản tóm tắt cực kỳ dài và toàn diện dựa trên phụ đề chi tiết của video yt này được cung cấp tại đây:\n\n {captions}\n\n đảm bảo nó dài {summary_length} từ.Đây là link video: {yt_url} cùng với tiêu đề của nó: {yt_title} từ kênh youtube: {yt_author}"
        else:
            message = f"Vui lòng cung cấp bản tóm tắt dài và đầy đủ dựa trên phụ đề chi tiết của video yt này được cung cấp tại đây:\n\n {captions}\n\n đảm bảo nó dài {summary_length} từ.Đây là link video: {yt_url} cùng với tiêu đề của nó: {yt_title} từ kênh youtube: {yt_author}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant for YTRecap, a webapp that provides very comprehensive and lengthy summaries for any provided youtube video (via input url)"},
                {"role": "user", "content": message}
            ],
            max_tokens=1200,
            n=1,
            stop=None,
            temperature=0.5,
        )
        # Remove newlines and extra spaces from summary
        summary = response.choices[0].message.content.strip()
        return summary

    except openai.error.InvalidRequestError:
        # Return error message if summary cannot be generated
        summaryNoCaptions = generateSummaryNoCaptions(summary_length, yt_url, yt_title, yt_description, yt_author)
        return summaryNoCaptions

#  - This is a fallback function to generate a summary when no captions are provided by YouTube
# - This function is called when the video is too long (causes character limit to openAI API, or there are no captions)
def generateSummaryNoCaptions(summary_length, url, yt_title, yt_description, yt_author):
    if summary_length >= 300:
        message = f"Vui lòng cung cấp một bản tóm tắt toàn diện cực kỳ dài và sâu sắc về video này \n\n URL: {url} \n\n Vui lòng đảm bảo độ dài tóm tắt xấp xỉ {summary_length} từ. Vui lòng sử dụng tiêu đề của video ở đây {yt_title} \n\n và tên kênh ở đây {yt_author} \n\n và mô tả ở đây: {yt_description} để cung cấp cái nhìn tổng quan tóm tắt về video"
    else:
        message = f"Vui lòng cung cấp bản tóm tắt chuyên sâu về video này \n\n. URL: {url} \n\n Vui lòng đảm bảo độ dài tóm tắt xấp xỉ {summary_length} từ. Vui lòng sử dụng tiêu đề của video ở đây {yt_title} \n\n và tên kênh ở đây \n\n {yt_author} và mô tả ở đây: \n\n {yt_description} để cung cấp cái nhìn tổng quan tóm tắt về video"
    print("Parsing API without captions due to long video OR not captions (or both)...")
    try: 
      response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant for YTRecap, a webapp that provides very comprehensive and lengthy summaries for any provided youtube video (via input url)"},
                {"role": "user", "content": message}
            ],
            max_tokens=1200,
            n=1,
            stop=None,
            temperature=0.5,
        )
    except: 
        # Return error message if summary cannot be generated
        summary = "Uh oh! Sorry, we couldn't generate a summary for this video and this error was not handled. Please visit source-code: https://github.com/nicktill/YTRecap/issues and open a new issue if possibe (it is likely due to the content of the yt video description being too long, exceeding the character limit of the OpenAI API).  "
        return summary
    # Remove newlines and extra spaces from summary
    summary = response.choices[0].message.content.strip()
    return summary

# Generating Video Summary 
@st.cache_data(show_spinner=False)
def generate_summary(url: str, sum_len: int) -> str:

    openai.api_key = OPENAI_KEY

    llm = OpenAI(temperature=0, openai_api_key=OPENAI_KEY, model_name="gpt-3.5-turbo")
    text_splitter = CharacterTextSplitter()

    # Extract the video_id from the url
    query = urlparse(url).query
    params = parse_qs(query)
    video_id = params["v"][0]

    # The path of the transcript
    transcript_filepath = f"tmp/{video_id}.txt"
    audio_path = f"tmp/{video_id}.mp3"

    # Check if the transcript file not exist
    if not os.path.exists(transcript_filepath):
        transcribe_youtube(video_id)
        # Generating summary of the text file
        with open(transcript_filepath) as f:
            content = f.read()
    else: 
        # Generating summary of the text file
        with open(transcript_filepath) as f:
            content = f.read()
    if not content:
        download_audio(url)

        # Transcribe the mp3 audio to text
        transcribe_audio(audio_path, video_id)

        # Generating summary of the text file
        with open(transcript_filepath) as f:
            content = f.read()

    author, title, description = get_video_information(YOUTUBE_API_KEY, video_id)

    if content:
        summary = generateSummaryWithCaptions(content, sum_len, url, title, description, author)
    else:
        summary = generateSummaryWithCaptions(sum_len, url, title, description, author)
    
    # summary = translateToVietnamese(summary.strip())

    return summary.strip()

@st.cache_data(show_spinner=False)
def generate_audio(text):
    tts = gTTS(text, lang='vi')  # 'vi' for Vietnamese
    audio_file = tempfile.NamedTemporaryFile(delete=False)
    tts.save(audio_file.name)
    audio_path = audio_file.name
    return audio_path
