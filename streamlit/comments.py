import streamlit as st
from googleapiclient.discovery import build
from pytube import extract
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

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

def get_comments_thread(youtube, video_id, results=None, next_page_token=""):
    if results is None:
        results = []

    if len(results) >= 1000:
        return results

    response = youtube.commentThreads().list(
        part="snippet",                     
        videoId=video_id,
        textFormat='plainText',
        pageToken=next_page_token,
        maxResults=100,
    ).execute()

    results = results + response["items"]

    # Get all comments
    if "nextPageToken" in response:
        return get_comments_thread(youtube, video_id, results, response["nextPageToken"])
    else:
        return results

def load_comments_in_format(comments):
    all_comments = []
    all_comments_string = ""
    for thread in comments:
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
    data = get_comments_thread(youtube, video_id, [], next_page_token)

    return data

def get_comments_sentiment(arr):
    results = []
    analyzer = SentimentIntensityAnalyzer()
    for item in arr:
        comment = item['snippet']['topLevelComment']['snippet']['textDisplay']

        sentiment = analyzer.polarity_scores(comment)

        if sentiment['compound'] > 0:
            sentiment_label = 'Positive'
        elif sentiment['compound'] < 0:
            sentiment_label = 'Negative'
        else:
            sentiment_label = 'Neutral'
        results.append((comment, sentiment_label))
    return results

def vn_polarity(comment):
    analyzer = SentimentIntensityAnalyzer()
    sentiment = analyzer.polarity_scores(comment)

    return sentiment['compound']
