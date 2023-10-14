import nltk
import openai
import streamlit as st
import transformers
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from dotenv import load_dotenv
from typing import List
import os
import time

load_dotenv()
nltk.download('punkt')

load_dotenv()

openai.api_key = os.environ.get('OPENAI_API_KEY')

def summarize_chunk(chunk: str, max_tokens: int = 1200, temperature: int = 0.5) -> str:
    message = f"Vui lòng cung cấp bản tóm tắt cực kỳ dài và toàn diện dựa trên các câu đánh giá video {chunk}"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Bạn là trợ lý AI cho Comment Youtube Summarized, một ứng dụng web cung cấp các bản tóm tắt rất toàn diện và dài dòn dựa trên các câu đánh giá của bất kỳ video youtube nào."},
            {"role": "user", "content": message}
        ],
        max_tokens=max_tokens,
        n=1,
        stop=None,
        temperature=temperature,
    )

    return response.choices[0].message.content.strip()