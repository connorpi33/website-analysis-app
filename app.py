import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

st.set_page_config(
    page_title="Domain Intelligence Analyzer",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Domain Intelligence Analyzer")

uploaded_file = st.file_uploader(
    "Upload a CSV containing a column named 'domain'",
    type=["csv"]
)

@st.cache_resource
def load_model():
    return pipeline("summarization")

summarizer = load_model()

def analyze_domain(domain):
    result = {
        "domain": domain,
        "status": "",
        "title": "",
        "description": "",
        "ai_summary": ""
    }

    try:
        url = f"https://{domain}"

        response = requests.get(url, timeout=10)

        result["status"] = response.status_code

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string if soup.title else ""

        description = ""

        meta = soup.find("meta", attrs={"name": "description"})

        if meta and meta.get("content"):
            description = meta["content"]

        result["title"] = title
        result["description"] = description

        text_for_ai = f"""
        Website title: {title}

        Description: {description}
        """

        summary = summarizer(
            text_for_ai,
            max_length=40,
            min_length=10,
            do_sample=False
        )

        result["ai_summary"] = summary[0]["summary_text"]

    except Exception as e:
        result["status"] = f"Error: {str(e)}"

    return result

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    if "domain" not in df.columns:
        st.error("CSV must contain a 'domain' column")

    else:

        results = []

        progress = st.progress(0)

        for i, domain in enumerate(df["domain"]):

            results.append(analyze_domain(domain))

            progress.progress((i + 1) / len(df))

        results_df = pd.DataFrame(results)

        st.dataframe(results_df, use_container_width=True)

        csv = results_df.to_csv(index=False)

        st.download_button(
            "Download Results CSV",
            csv,
            "domain_analysis.csv",
            "text/csv"
        )
