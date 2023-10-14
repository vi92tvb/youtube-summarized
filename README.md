### Installation : 
PYTHON 3.10.0
1. Clone the repository:

2. Install the required packages:

```
pip install -r requirements.txt
```

### Usage : 

1. Go to the streamlit/ folder:

```
cd streamlit/
```

2. Ensure your Youtube API keys are set as `API_SERVICE_NAME`, `API_VERSION`, `YOUTUBE_API_KEY` in the secrets.toml file (check the secrets.toml.example file for reference). Please find the details to generate the API key [here.](https://developers.google.com/youtube/registering_an_application)

3. Ensure your OpenAI API key is set as an environment variable `OPENAI_API_KEY` in the secrets.toml file (check the secrets.toml.example file for reference). (see best practices around API key safety [here](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety))
  
4. Run the app:

```
streamlit run 01_🎬_YouTube.py
```

5. Go to your localhost : http://localhost:8502/

6. Enter the OpenAI API Key followed by YouTube video URL and the question you want to ask.