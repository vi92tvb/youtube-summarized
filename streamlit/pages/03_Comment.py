import transformers
import streamlit as st
from comments import fetch_comments
from utils import summarize_chunk

st.set_page_config(page_title="Comment Summarized", page_icon='💬')

def comment_summarized():
    st.title("Youtube Comments Summarizer")

    st.write(
        "Use this tool to generate summaries from comments under any Youtube video."
        "The Tool uses OpenAI's APIs to generate the summaries."
    )
    st.write(
        "The app is currently a POC. It extracts comments from the selected Youtube video, "
        "chunks the text, summarizes it and then returns the same."
    )

    st.write()

    left, right = st.columns(2)
    form = left.form("template_form")

    url_input = form.text_input(
        "Enter Youtube video url",
        placeholder="",
        value="",
    )

    submit = form.form_submit_button("Get Summary")

    if submit and url_input:
        with st.spinner("Fetching Summary..."):
            text = fetch_comments(url_input)
            print("==================== COMMENT ====================")
            with st.spinner("Đang tạo tóm tắt..."):
                summary = summarize_chunk(text)
            st.markdown(f"#### 📃 Nội dung bình luận tóm tắt:")

            # with right:
            st.success(summary)

comment_summarized()

# Hide Left Menu
st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>""", unsafe_allow_html=True)