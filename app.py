import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

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

def analyze_domain(domain):
    result = {
        "domain": domain,
        "status": "",
        "title": "",
        "description": "",
        "site_summary": ""
    }

    try:
        domain = str(domain).replace("https://", "").replace("http://", "").strip("/")
        url = f"https://{domain}"

        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        result["status"] = response.status_code

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        meta = soup.find("meta", attrs={"name": "description"})
        description = meta["content"].strip() if meta and meta.get("content") else ""

        result["title"] = title
        result["description"] = description

        if description:
            result["site_summary"] = description
        elif title:
            result["site_summary"] = f"This site appears to be related to: {title}"
        else:
            result["site_summary"] = "No clear site description found."

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
