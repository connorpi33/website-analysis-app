import streamlit as st
import pandas as pd
import requests
import whois
from bs4 import BeautifulSoup
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest
from google.oauth2 import service_account
from anthropic import Anthropic

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

def generate_ai_assessment(result):
    try:
        client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

        prompt = f"""
        Analyze this domain using the available data.

        Domain: {result.get("domain")}
        Title: {result.get("title")}
        Description: {result.get("description")}
        Tech stack: {result.get("tech_stack")}
        Registrar: {result.get("registrar")}
        Creation date: {result.get("creation_date")}
        Expiration date: {result.get("expiration_date")}
        WHOIS country: {result.get("whois_country")}
        GA4 active users: {result.get("ga4_active_users")}
        GA4 sessions: {result.get("ga4_sessions")}
        GA4 pageviews: {result.get("ga4_pageviews")}

        Write a concise plain-English assessment of what this domain appears to be,
        whether anything looks notable, and what action someone should take next.
        Keep it to 2-3 sentences.
        """

        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=200,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    except Exception as e:
        return f"AI assessment unavailable: {str(e)}"

def get_ga4_traffic(property_id):
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )

        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews")
            ],
        )

        response = client.run_report(request)

        if not response.rows:
            return {
                "ga4_active_users": 0,
                "ga4_sessions": 0,
                "ga4_pageviews": 0
            }

        row = response.rows[0]

        return {
            "ga4_active_users": row.metric_values[0].value,
            "ga4_sessions": row.metric_values[1].value,
            "ga4_pageviews": row.metric_values[2].value
        }

    except Exception as e:
        return {
            "ga4_active_users": "Unavailable",
            "ga4_sessions": "Unavailable",
            "ga4_pageviews": f"Error: {str(e)}"
        }

def get_whois_details(domain):
    details = {
        "registrar": "",
        "creation_date": "",
        "expiration_date": "",
        "whois_country": ""
    }

    try:
        w = whois.whois(domain)

        details["registrar"] = w.registrar
        details["creation_date"] = str(w.creation_date)
        details["expiration_date"] = str(w.expiration_date)
        details["whois_country"] = w.country

    except Exception as e:
        details["registrar"] = "Unavailable"

    return details

def detect_tech(html, headers):
    html_lower = html.lower()
    tech = []

    if "wp-content" in html_lower or "wordpress" in html_lower:
        tech.append("WordPress")

    if "shopify" in html_lower or "cdn.shopify.com" in html_lower:
        tech.append("Shopify")

    if "wix.com" in html_lower or "wixstatic.com" in html_lower:
        tech.append("Wix")

    if "squarespace" in html_lower:
        tech.append("Squarespace")

    if "react" in html_lower or "__next_data__" in html_lower:
        tech.append("React / Next.js")

    if "vue" in html_lower:
        tech.append("Vue.js")

    if "angular" in html_lower:
        tech.append("Angular")

    if "googletagmanager.com" in html_lower:
        tech.append("Google Tag Manager")

    if "google-analytics.com" in html_lower or "gtag/js" in html_lower:
        tech.append("Google Analytics")

    if "hubspot" in html_lower:
        tech.append("HubSpot")

    if "cloudflare" in str(headers).lower():
        tech.append("Cloudflare")

    if "server" in headers:
        server = headers.get("server", "")
        if server:
            tech.append(f"Server: {server}")

    return ", ".join(sorted(set(tech))) if tech else "Unknown"

# Result Dictionary
def analyze_domain(domain, row=None):
    result = {
    "domain": domain,
    "status": "",
    "title": "",
    "description": "",
    "site_summary": "",
    "tech_stack": "",
    "registrar": "",
    "creation_date": "",
    "expiration_date": "",
    "whois_country": "",
    "ga4_active_users": "",
    "ga4_sessions": "",
    "ga4_pageviews": "",
    "ai_assessment": ""
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
        result["tech_stack"] = detect_tech(response.text, response.headers)

        # WHOIS SECTION
        whois_details = get_whois_details(domain)

        result["registrar"] = whois_details["registrar"]
        result["creation_date"] = whois_details["creation_date"]
        result["expiration_date"] = whois_details["expiration_date"]
        result["whois_country"] = whois_details["whois_country"]

        # GA4 SECTION
        ga4_property_id = row.get("ga4_property_id", "") if row is not None else ""

        if pd.notna(ga4_property_id) and str(ga4_property_id).strip() != "":
            ga4_property_id = str(int(float(ga4_property_id)))

            ga4_details = get_ga4_traffic(ga4_property_id)

            result["ga4_active_users"] = ga4_details["ga4_active_users"]
            result["ga4_sessions"] = ga4_details["ga4_sessions"]
            result["ga4_pageviews"] = ga4_details["ga4_pageviews"]
        else:
            result["ga4_active_users"] = "No GA4 property ID"
            result["ga4_sessions"] = "No GA4 property ID"
            result["ga4_pageviews"] = "No GA4 property ID"

        if description:
            result["site_summary"] = description
        elif title:
            result["site_summary"] = f"This site appears to be related to: {title}"
        else:
            result["site_summary"] = "No clear site description found."

        result["ai_assessment"] = generate_ai_assessment(result)
    
    except Exception as e:
        result["status"] = f"Error: {str(e)}"
        result["tech_stack"] = "Unknown"

    return result

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    if "domain" not in df.columns:
        st.error("CSV must contain a 'domain' column")
    else:
        results = []
        progress = st.progress(0)

        for i, row in df.iterrows():
            results.append(analyze_domain(row["domain"], row))
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
