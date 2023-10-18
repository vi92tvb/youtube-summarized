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
from googletrans import Translator
from googleapiclient.discovery import build
from gtts import gTTS
import tempfile
import os
from utils import summarize_comment
from Shorten_Video import convert_video_shot_change
from comments import get_comments_sentiment
import matplotlib.pyplot as plt

load_dotenv()

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

def tmp_folder_creating():
    # Define the folder path
    folder_path = "tmp"

    # Check if the folder exists, and create it if it doesn't
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

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

# Transcription 
def transcribe_youtube(video_id):
    tmp_folder_creating()
    transcript_filepath = f"tmp/{video_id}.txt"
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)


        captions = []
        for transcript in transcript_list:
            captions.extend(transcript.translate('vi').fetch())
        with open(transcript_filepath, 'w', encoding='utf-8') as transcript_file:
            transcript_file.write(parse_text_info(captions))
        print("Transcript written successfully.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        captions = None

# Function to generate summary using OpenAI API
def generate_summary_with_captions(captions, summary_length, yt_url, yt_title, yt_description, yt_author):
    try:
        if summary_length >= 300:
            message = f"Vui lòng cung cấp bản tóm tắt cực kỳ dài và toàn diện dựa trên phụ đề chi tiết của video youtube này được cung cấp tại đây:\n\n {captions}\n\n đảm bảo nó dài {summary_length} từ. Đây là link video: {yt_url} cùng với tiêu đề của nó: {yt_title} từ kênh youtube: {yt_author}"
        else:
            message = f"Vui lòng cung cấp bản tóm tắt dài và đầy đủ dựa trên phụ đề chi tiết của video youtube này được cung cấp tại đây:\n\n {captions}\n\n đảm bảo nó dài {summary_length} từ. Đây là link video: {yt_url} cùng với tiêu đề của nó: {yt_title} từ kênh youtube: {yt_author}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Bạn là trợ lý AI cho Youtube Summarized, một ứng dụng web cung cấp các bản tóm tắt rất toàn diện và dài dòng cho bất kỳ video youtube nào được cung cấp (thông qua url đầu vào))"},
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
        summaryNoCaptions = generate_summary_no_captions(summary_length, yt_url, yt_title, yt_description, yt_author)
        return summaryNoCaptions

# This is a fallback function to generate a summary when no captions are provided by YouTube
def generate_summary_no_captions(summary_length, url, yt_title, yt_description, yt_author):
    if summary_length >= 300:
        message = f"Vui lòng cung cấp một bản tóm tắt toàn diện cực kỳ dài và sâu sắc về video này \n\n URL: {url} \n\n Vui lòng đảm bảo độ dài tóm tắt xấp xỉ {summary_length} từ. Vui lòng sử dụng tiêu đề của video ở đây {yt_title} \n\n và tên kênh ở đây {yt_author} \n\n và mô tả ở đây: {yt_description} để cung cấp cái nhìn tổng quan tóm tắt về video"
    else:
        message = f"Vui lòng cung cấp bản tóm tắt chuyên sâu về video này \n\n. URL: {url} \n\n Vui lòng đảm bảo độ dài tóm tắt xấp xỉ {summary_length} từ. Vui lòng sử dụng tiêu đề của video ở đây {yt_title} \n\n và tên kênh ở đây \n\n {yt_author} và mô tả ở đây: \n\n {yt_description} để cung cấp cái nhìn tổng quan tóm tắt về video"
    try: 
      response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Bạn là trợ lý AI cho Youtube Summarized, một ứng dụng web cung cấp các bản tóm tắt rất toàn diện và dài dòng cho bất kỳ video youtube nào được cung cấp (thông qua url đầu vào)"},
                {"role": "user", "content": message}
            ],
            max_tokens=1200,
            n=1,
            stop=None,
            temperature=0.5,
        )
    except: 
        # Return error message if summary cannot be generated
        summary = "Xin lỗi chúng tôi không thể tóm tắt video này. "
        return summary
    # Remove newlines and extra spaces from summary
    summary = response.choices[0].message.content.strip()
    return summary

# Generating Video Summary 
@st.cache_data(show_spinner=False)
def generate_summary(url: str, sum_len: int) -> str:

    openai.api_key = OPENAI_API_KEY

    # Extract the video_id from the url
    query = urlparse(url).query
    params = parse_qs(query)
    video_id = params["v"][0]

    # The path of the transcript
    tmp_folder_creating()
    transcript_filepath = f"tmp/{video_id}.txt"

    # Check if the transcript file not exist
    if not os.path.exists(transcript_filepath):
        transcribe_youtube(video_id)
    try:
        with open(transcript_filepath, encoding='utf-8') as f:
            content = f.read()
    except (FileNotFoundError, IOError):
        content = ""
        pass

    author, title, description = get_video_information(YOUTUBE_API_KEY, video_id)

    if content:
        summary = generate_summary_with_captions(content, sum_len, url, title, description, author)
    else:
        summary = generate_summary_no_captions(sum_len, url, title, description, author)
    
    return summary.strip()

def video_folder_creating():
    # Define the folder path
    input_path = "video_input"
    output_path = "video_output"

    # Check if the folder exists, and create it if it doesn't
    if not os.path.exists(input_path):
        os.makedirs(input_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

@st.cache_data(show_spinner=False)
def generate_audio(text):
    tts = gTTS(text, lang='vi')  # 'vi' for Vietnamese
    audio_file = tempfile.NamedTemporaryFile(delete=False)
    tts.save(audio_file.name)
    audio_path = audio_file.name
    return audio_path

@st.cache_data(show_spinner=False)
def generate_comment_summary(text, sum_len):
    summary = summarize_comment(text, sum_len)
    return summary

@st.cache_data(show_spinner=False)
def generate_shorten_video(url):
    video_folder_creating()
    video_name = convert_video_shot_change(url)
    return video_name

@st.cache_data(show_spinner=False)
def generate_piechart(comments):
    results = get_comments_sentiment(comments)

    sentiment_counts = {
        'Positive': 0,
        'Neutral': 0,
        'Negative': 0
    }

    for comment, sentiment in results:
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1

    # Create a Streamlit app
    st.title("Sentiment Analysis with Pie Chart")
    st.write("Distribution of Sentiments in the Data")

    # Prepare the data for the pie chart
    labels = sentiment_counts.keys()
    sizes = sentiment_counts.values()

    # Create the pie chart
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    # Display the pie chart in Streamlit
    st.pyplot(fig)
