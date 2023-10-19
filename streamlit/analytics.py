"""
Function that does the transformation to pass onto streamlit
"""
import os
from dotenv import load_dotenv
import googleapiclient.discovery
import pandas as pd
from urllib.parse import urlparse, parse_qs
import pycountry
from cleantext import clean
from langdetect import detect, LangDetectException
from textblob import TextBlob
import streamlit as st
from functions import extract_video_id_from_link
from comments import get_comments_thread, vn_polarity
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # Import VADER

load_dotenv()

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

def get_polarity(text):
    return TextBlob(text).sentiment.polarity

def get_sentiment(polarity):
    if polarity > 0:
        return 'POSITIVE'
    if polarity < 0:
        return 'NEGATIVE'

    return 'NEUTRAL'


def det_lang(language):
    try:
        lang = detect(language)
    except LangDetectException:
        lang = 'Other'
    return lang


def parse_video(url) -> pd.DataFrame:
    # Extract the video_id from the url
    video_id = extract_video_id_from_link(url)


    # creating youtube resource object
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    video_response = get_comments_thread(youtube, video_id, [], "")

    # empty list for storing reply
    comments = []
    analyzer = SentimentIntensityAnalyzer()

    # extracting required info from each result object
    for item in video_response:

        # Extracting comments
        comment = item['snippet']['topLevelComment']['snippet']['textOriginal']
        # Extracting author
        author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
        # Extracting published time
        published_at = item['snippet']['topLevelComment']['snippet']['publishedAt']
        # Extracting likes
        like_count = item['snippet']['topLevelComment']['snippet']['likeCount']
        # Extracting total replies to the comment
        reply_count = item['snippet']['totalReplyCount']

        comments.append(
            [author, comment, published_at, like_count, reply_count])

    df_transform = pd.DataFrame({'Author': [i[0] for i in comments],
                                 'Comment': [i[1] for i in comments],
                                 'Timestamp': [i[2] for i in comments],
                                 'Likes': [i[3] for i in comments],
                                 'TotalReplies': [i[4] for i in comments]})

    # Remove extra spaces and make them lower case. Replace special emojis
    df_transform['Comment'] = df_transform['Comment'].apply(lambda x: x.strip().lower().
                                                            replace('xd', '').replace('<3', ''))
    # Detect the languages of the comments
    df_transform['Language'] = df_transform['Comment'].apply(det_lang)

    # Convert ISO country codes to Languages
    df_transform['Language'] = df_transform['Language'].apply(
        lambda x: pycountry.languages.get(alpha_2=x).name if (x) != 'Other' else 'Not-Detected')

    # Dropping Not detected languages
    df_transform.drop(
        df_transform[df_transform['Language'] == 'Not-Detected'].index, inplace=True)

    # Determining the polarity based on english comments
    df_transform['TextBlob_Polarity'] = df_transform[['Comment', 'Language']].apply(
        lambda x: get_polarity(x['Comment']) if x['Language'] == 'English'
                                             else (vn_polarity(x['Comment']) if x['Language'] == 'Vietnamese' else ''), axis=1)

    df_transform['TextBlob_Sentiment_Type'] = df_transform['TextBlob_Polarity'].apply(
        lambda x: get_sentiment(x) if isinstance(x, float) else '')

    # Change the Timestamp
    df_transform['Timestamp'] = pd.to_datetime(
        df_transform['Timestamp']).dt.strftime('%Y-%m-%d %r')

    return df_transform

def youtube_metrics(url) -> list:
    # Get the video_id from the url
    video_id = extract_video_id_from_link(url)

    # creating youtube resource object
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    statistics_request = youtube.videos().list(
        part="statistics",
        id=video_id
    ).execute()

    metrics = []

    # extracting required info from each result object
    for item in statistics_request['items']:

        # Extracting views
        metrics.append(item['statistics']['viewCount'])
        # Extracting likes
        metrics.append(item['statistics']['likeCount'])
        # Extracting Comments
        metrics.append(item['statistics']['commentCount'])

    return metrics
