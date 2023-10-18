import streamlit as st

from functions import generate_summary, video_info, is_valid_youtube_url, get_video_duration, generate_audio, generate_comment_summary, generate_shorten_video, generate_piechart
from comments import fetch_comments, load_comments_in_format
from IPython.display import Video
import concurrent.futures

st.set_page_config(page_title="Youtube Summarized", page_icon='🎬')

# App UI
def youtube_app():

    st.markdown('## 🎬 Tóm tắt YouTube Videos') 

    st.markdown('######') 
    
    st.markdown('#### 📼 Nhập URL của video trên Youtube')
    youtube_url = st.text_input("URL :", placeholder="https://www.youtube.com/watch?v=************")

    if is_valid_youtube_url(youtube_url):
        video_duration = get_video_duration(youtube_url)

        if video_duration >= 5:
            st.info(f"🕖 Độ dài video là {video_duration} phút. Thời gian tóm tắt có thể lâu hơn dự kiến.")
        else:
            st.info(f"🕖 Độ dài video là {video_duration} phút.")
        thumbnail_url, video_title = video_info(youtube_url)
        st.markdown(f"#### 📽️ {video_title}")
        st.image(f"{thumbnail_url}", use_column_width='always')
    else:
        st.error("Vui lòng nhập URL video YouTube")


    if youtube_url:
        summary_length_mapping = {
            'Ngắn': 100,
            'Vừa': 200,
            'Dài': 300
        }

        selected_length = summary_length_mapping[st.selectbox("Chọn độ dài tóm tắt:", list(summary_length_mapping.keys()))]
        if selected_length and st.button("Tạo tóm tắt"):
            if not youtube_url:
                st.warning("Hãy nhập URL Youtube khả dụng")
            else:
                with st.spinner("Đang tạo tóm tắt..."):
                    # Create a ThreadPoolExecutor
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # Submit the functions to the executor and store the Future objects
                        future_summary = executor.submit(generate_summary, youtube_url, selected_length)
                        future_audio = executor.submit(generate_audio, future_summary.result())
                        future_comments = executor.submit(fetch_comments, youtube_url)
                        future_summary_comment = executor.submit(generate_comment_summary, load_comments_in_format(future_comments.result()), selected_length)
                        future_piechart = executor.submit(generate_piechart, future_comments.result())
                        future_shorten_video = executor.submit(generate_shorten_video, youtube_url)

                st.markdown(f"#### 📃 Nội dung tóm tắt video:")
                result_summary = st.empty()
                result_summary.success(future_summary.result())

                st.markdown(f"#### 🔊 Audio nội dung tóm tắt:")
                result_audio = st.empty()
                with st.spinner("Đang tạo âm thanh ..."):
                    result_audio.audio(future_audio.result())

                st.markdown(f"#### 📃 Nội dung tóm tắt bình luận:")
                result_comment = st.empty()
                result_comment.success(future_summary_comment.result())

                st.markdown(f"#### 📃 Biểu đồ đánh giá cảm xúc của đánh giá video:")
                result_piechart = st.empty()
                result_piechart.pyplot(future_piechart.result())

                st.markdown(f"#### 📃 Video tóm tắt ngắn chứa các chuyển cảnh:")
                result_video = st.empty()
                with st.spinner("Đang tạo video..."):
                    result_video.video(open(future_shorten_video.result(), 'rb').read())
    else:
        st.warning("YouTube URL không đúng hoặc không khả dụng")

youtube_app()

# Hide Left Menu
st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>""", unsafe_allow_html=True)
