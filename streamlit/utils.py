import nltk
import openai
from dotenv import load_dotenv
import os

load_dotenv()
nltk.download('punkt')

load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')

def summarize_comment(chunk: str, summary_length: int) -> str:
    message = f"Vui lòng cung cấp bản tóm tắt cực kỳ dài và toàn diện dựa trên các câu đánh giá video {chunk} \n\n Vui lòng đảm bảo độ dài tóm tắt xấp xỉ {summary_length} từ."
    message = message[:4090]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Bạn là trợ lý AI cho Comment Youtube Summarized, một ứng dụng web cung cấp các bản tóm tắt rất toàn diện và dài dòn dựa trên các câu đánh giá của bất kỳ video youtube nào."},
            {"role": "user", "content": message}
        ],
        max_tokens=1200,
        n=1,
        stop=None,
        temperature=0.5,
    )

    return response.choices[0].message.content.strip()