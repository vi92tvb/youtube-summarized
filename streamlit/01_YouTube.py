import streamlit as st

from functions import generate_summary, video_info, is_valid_youtube_url, get_video_duration, generate_audio, generate_comment_summary, generate_shorten_video
from comments import fetch_comments, load_comments_in_format
from IPython.display import Video
import concurrent.futures

import json
import streamlit as st
from streamlit_echarts import st_echarts
from millify import millify
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from analytics import parse_video, youtube_metrics

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
                with st.spinner("Đang tóm tắt và thống kê..."):
                    # Create a ThreadPoolExecutor
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # Submit the functions to the executor and store the Future objects
                        future_summary = executor.submit(generate_summary, youtube_url, selected_length)
                        future_audio = executor.submit(generate_audio, future_summary.result())
                        future_comments = executor.submit(fetch_comments, youtube_url)
                        future_summary_comment = executor.submit(generate_comment_summary, load_comments_in_format(future_comments.result()), selected_length)
                        future_shorten_video = executor.submit(generate_shorten_video, youtube_url)
                        future_df = executor.submit(parse_video, youtube_url)
                        future_df_metrics = executor.submit(youtube_metrics, youtube_url)

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

                st.markdown(f"#### 📃 Video tóm tắt ngắn chứa các chuyển cảnh:")
                result_video = st.empty()
                with st.spinner("Đang tạo video..."):
                    result_video.video(open(future_shorten_video.result(), 'rb').read())

                st.markdown(f"#### 📃 Thống kê đánh giá cảm xúc của đánh giá video:")
                df = future_df.result()
                df_metrics = future_df_metrics.result()

                # Metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("**Lượt xem**", millify(df_metrics[0], precision=2))
                col2.metric("**Lượt thích**", millify(df_metrics[1], precision=2))
                col3.metric("**Số bình luận**", millify(df_metrics[2], precision=2))

                # Top Comments
                st.subheader("Top bình luận nhiều lượt thích nhất")
                df_top = df[['Author', 'Comment', 'Timestamp', 'Likes']].sort_values(
                    'Likes', ascending=False).reset_index(drop=True)

                gd1 = GridOptionsBuilder.from_dataframe(df_top.head(11))
                gridoptions1 = gd1.build()
                AgGrid(df_top.head(11), gridOptions=gridoptions1,
                    theme='streamlit', columns_auto_size_mode='FIT_CONTENTS',
                    update_mode='NO_UPDATE')

                # Top Languages
                st.subheader("Ngôn ngữ")
                df_langs = df['Language'].value_counts().rename_axis(
                    'Language').reset_index(name='count')

                options2 = {
                    "tooltip": {
                        "trigger": 'axis',
                        "axisPointer": {
                            "type": 'shadow'
                        },
                        "formatter": '{b}: {c} bình luận'
                    },
                    "yAxis": {
                        "type": "category",
                        "data": df_langs['Language'].tolist(),
                    },
                    "xAxis": {"type": "value",
                            "axisTick": {
                                "alignWithLabel": "true"
                            }
                            },
                    "series": [{"data": df_langs['count'].tolist(), "type": "bar"}],
                }
                st_echarts(options=options2, height="500px")

                # Most Replied Comments
                st.subheader("Top bình luận nhiều lượt trả lời nhất")
                df_replies = df[['Author', 'Comment', 'Timestamp', 'TotalReplies']].sort_values(
                    'TotalReplies', ascending=False).reset_index(drop=True)
                # st.dataframe(df_replies.head(11))

                gd2 = GridOptionsBuilder.from_dataframe(df_replies.head(11))
                gridoptions2 = gd2.build()
                AgGrid(df_replies.head(11), gridOptions=gridoptions2,
                    theme='streamlit', columns_auto_size_mode='FIT_CONTENTS',
                    update_mode='NO_UPDATE')

                # Sentiments of the Commentors
                st.subheader("Biểu đồ phân bố cảm xúc bình luận")
                sentiments = df[(df['Language'] == 'English') | (df['Language'] == 'Vietnamese')]
                data_sentiments = sentiments['TextBlob_Sentiment_Type'].value_counts(
                ).rename_axis('Sentiment').reset_index(name='counts')
            
                data_sentiments['Review_percent'] = (
                    100. * data_sentiments['counts'] / data_sentiments['counts'].sum()).round(1)

                result = data_sentiments.to_json(orient="split")
                parsed = json.loads(result)
                data = []

                for item in parsed['data']:
                    data.append({"value": item[2],
                                "name": item[0]})
                    
                options = {
                    "tooltip": {"trigger": "item",
                                "formatter": '{d}%'},
                    "legend": {"top": "5%", "left": "center"},
                    "series": [
                        {
                            "name": "Sentiment",
                            "type": "pie",
                            "radius": ["40%", "70%"],
                            "avoidLabelOverlap": False,
                            "itemStyle": {
                                "borderRadius": 10,
                                "borderColor": "#fff",
                                "borderWidth": 2,
                            },
                            "label": {"show": False, "position": "center"},
                            "emphasis": {
                                "label": {"show": True, "fontSize": "30", "fontWeight": "bold"}
                            },
                            "labelLine": {"show": False},
                            "data": data,
                        }
                    ],
                }
                st_echarts(
                    options=options, height="500px",
                )
    else:
        st.warning("YouTube URL không đúng hoặc không khả dụng")

youtube_app()

# Hide Left Menu
st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>""", unsafe_allow_html=True)
