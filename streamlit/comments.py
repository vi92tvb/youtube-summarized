import streamlit as st
from googleapiclient.discovery import build
from pytube import extract
import os
from google.cloud import translate_v2 as translate
import regex as re
import string
import numpy as np
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

def split_list_by_length(strings, max_length):
    sublists = []
    current_sublist = []

    for string in strings:
        if sum(len(s) for s in current_sublist) + len(string) <= max_length:
            current_sublist.append(string)
        else:
            sublists.append(current_sublist)
            current_sublist = [string]

    if current_sublist:
        sublists.append(current_sublist)

    return sublists

def extract_text_from_html(html_string):
    p_text_list = []

    start_index = 0
    while start_index < len(html_string):
        start_p = html_string.find("<p>", start_index)
        if start_p == -1:
            break
        end_p = html_string.find("</p>", start_p)
        if end_p == -1:
            break

        p_text = html_string[start_p + 3:end_p]
        p_text_list.append(p_text)

        start_index = end_p + 4

    return p_text_list

def translate_to_english(input_text):
  client = translate.Client()

  target_language_code = "en"

  translation = client.translate(input_text, target_language=target_language_code)
  return (f"{translation['translatedText']}")

def convert_comment_to_arr(arr):
    comments = []
    for item in arr:
        comment = item['snippet']['topLevelComment']['snippet']['textOriginal']
        comments.append("<p>" + comment + "</p>")
    return comments
