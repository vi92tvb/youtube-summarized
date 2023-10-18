import streamlit as st
from googleapiclient.discovery import build
from pytube import extract
import os

from dotenv import load_dotenv
import nltk
nltk.download('punkt')

# Load env
load_dotenv()

API_SERVER_NAME = os.environ.get("API_SERVICE_NAME")
API_VERSION = os.environ.get("API_VERSION")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

def start_youtube_service():
     return build(API_SERVER_NAME, API_VERSION, developerKey=YOUTUBE_API_KEY)

def extract_video_id_from_link(url):
    return extract.video_id(url)

def get_comments_thread(youtube, video_id, next_page_token):
    results = youtube.commentThreads().list(
        part="snippet,replies",                     
        videoId=video_id,
        textFormat='plainText',
        maxResults=100,
    ).execute()
    return results

def load_comments_in_format(comments):
    all_comments = []
    all_comments_string = ""
    for thread in comments["items"]:
        comment = {}
        comment['content'] = thread['snippet']['topLevelComment']['snippet']['textOriginal']
        all_comments_string = all_comments_string + comment['content']+"\n"
        replies = []
        if 'replies' in thread:
            for reply in thread['replies']['comments']:
                reply_text = reply['snippet']['textOriginal']
                all_comments_string = all_comments_string + reply_text+"\n"
                replies.append(reply_text)
            comment['replies'] = replies
        
        all_comments.append(comment)
    return all_comments_string

def fetch_comments(url):
    youtube = start_youtube_service()
    video_id = extract_video_id_from_link(url)
    next_page_token = ''
   
    data = get_comments_thread(youtube, video_id, next_page_token)

    all_comments = load_comments_in_format(data)
    return all_comments