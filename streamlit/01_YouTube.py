import streamlit as st

from functions import generate_summary, video_info, is_valid_youtube_url, get_video_duration, generate_audio, generate_comment_summary, generate_shorten_video, generate_piechart
from comments import fetch_comments, load_comments_in_format
from IPython.display import Video

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
                    # Call the function with the user inputs
                    summary = generate_summary(youtube_url, selected_length)

                st.markdown(f"#### 📃 Nội dung tóm tắt video:")
                st.success(summary)

                st.markdown(f"#### 🔊 Audio nội dung tóm tắt:")
                with st.spinner("Đang tạo âm thanh ..."):
                     audio_path = generate_audio(summary)
                # Play the Vietnamese audio in the app
                st.audio(audio_path)

                st.markdown(f"#### 📃 Nội dung tóm tắt bình luận:")
                with st.spinner("Đang tạo tóm tắt bình luận..."):
                    # Call the function with the user inputs
                    comments = fetch_comments(youtube_url)
                    instance = comments
                    summary_comment = generate_comment_summary(load_comments_in_format(instance), selected_length)
                st.success(summary_comment)

                st.markdown(f"#### 📃 Biểu đồ đánh giá cảm xúc của đánh giá video:")
                with st.spinner("Đang tạo biểu đồ..."):
                    generate_piechart(comments)

                st.markdown(f"#### 📃 Video tóm tắt ngắn chứa các chuyển cảnh:")
                with st.spinner("Đang tạo video..."):
                    # Call the function with the user inputs
                    video_url = generate_shorten_video(youtube_url)
                    video  = open(video_url, 'rb').read()
                st.video(video)
    else:
        st.warning("YouTube URL không đúng hoặc không khả dụng")
        
youtube_app()

# Hide Left Menu
st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>""", unsafe_allow_html=True)



