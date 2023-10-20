"""
Function that does the transformation to pass onto streamlit
"""
import os
import time
from dotenv import load_dotenv
import googleapiclient.discovery
import pandas as pd
import pycountry
from langdetect import detect, LangDetectException
from textblob import TextBlob
import streamlit as st
from functions import extract_video_id_from_link
from comments import extract_text_from_html, get_comments_thread, split_list_by_length, translate_to_english, convert_comment_to_arr

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

def get_language_name(x):
    if x != 'Other':
        language = pycountry.languages.get(alpha_2=x)
        if language is not None:
            return language.name
    return 'Not-Detected'

def parse_video(url) -> pd.DataFrame:
    # Extract the video_id from the url
    video_id = extract_video_id_from_link(url)


    # creating youtube resource object
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    video_response = get_comments_thread(youtube, video_id, [], "")

    # empty list for storing reply
    comments = []

    # translate comment to english
    list_of_sublist_comments = split_list_by_length(convert_comment_to_arr(video_response), max_length=5000)
    list_eng_comment = []

    for i, sublist in enumerate(list_of_sublist_comments, start=1):
        print(f"Lần gọi lên gg tran api thứ: {i}:")
        combined_text = "\n".join(sublist)

        eng_comment = translate_to_english(combined_text)

        sublist_eng_comment = extract_text_from_html(eng_comment)
        list_eng_comment.extend(sublist_eng_comment)

    for item, trans in zip(video_response, list_eng_comment):
        # Extracting comments
        comment = item['snippet']['topLevelComment']['snippet']['textOriginal']
        translated = trans
        # Extracting author
        author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
        # Extracting published time
        published_at = item['snippet']['topLevelComment']['snippet']['publishedAt']
        # Extracting likes
        like_count = item['snippet']['topLevelComment']['snippet']['likeCount']
        # Extracting total replies to the comment
        reply_count = item['snippet']['totalReplyCount']

        comments.append(
            [author, comment, translated, published_at, like_count, reply_count])

    df_transform = pd.DataFrame({'Author': [i[0] for i in comments],
                                'Comment': [i[1] for i in comments],
                                'Translated': [i[2] for i in comments],
                                'Timestamp': [i[3] for i in comments],
                                'Likes': [i[4] for i in comments],
                                'TotalReplies': [i[5] for i in comments]})

    # Remove extra spaces and make them lower case. Replace special emojis
    df_transform['Comment'] = df_transform['Comment'].apply(lambda x: x.strip().lower())

    # Detect the languages of the comments
    df_transform['Language'] = df_transform['Comment'].apply(det_lang)

    # Convert ISO country codes to Languages
    # df_transform['Language'] = df_transform['Language'].apply(
    #     lambda x: pycountry.languages.get(alpha_2=x).name if (x) != 'Other' else 'Not-Detected')
    df_transform['Language'] = df_transform['Language'].apply(get_language_name)

    # Dropping Not detected languages
    df_transform.drop(
        df_transform[df_transform['Language'] == 'Not-Detected'].index, inplace=True)

    # Sentiment
    df_transform['TextBlob_Polarity'] = df_transform[['Translated', 'Language']].apply(
        lambda x: get_polarity(x['Translated']), axis=1)

    df_transform['TextBlob_Sentiment_Type'] = df_transform['TextBlob_Polarity'].apply(
        lambda x: get_sentiment(x) if isinstance(x, float) else '')


    # Change the Timestamp
    df_transform['Timestamp'] = pd.to_datetime(
        df_transform['Timestamp']).dt.strftime('%Y-%m-%d %r')

    print(df_transform)
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
