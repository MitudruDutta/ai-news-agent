# file: app.py
"""
Modern AI News Agent - Streamlit Interface
Enhanced UI with dynamic sources, real-time search, and sleek design
"""

import streamlit as st
from datetime import datetime
import time
import os
from pathlib import Path
import json

# Configure page FIRST
st.set_page_config(
    page_title="AI Intelligence Hub",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Imports
try:
    from agent_crew import run_crew
    from news_fetcher import fetch_recent_articles
    from audio_generator import generate_audio_briefing
    from sources_config import (
        get_sources_by_profile,
        get_active_sources_count,
        get_sources_by_category,
        PROFILE_MAP
    )

    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    st.error(f"Import error: {e}")

# ==================== MODERN STYLING ====================

st.markdown("""
<style>
    /* Modern Color Scheme */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --secondary: #8b5cf6;
        --accent: #ec4899;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --bg-dark: #0f172a;
        --bg-card: #1e293b;
        --text-light: #f1f5f9;
        --text-muted: #94a3b8;
        --border: #334155;
    }

    /* Main App Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }

    /* Header Section */
    .main-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 60px rgba(99, 102, 241, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .main-header h1 {
        color: white;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        letter-spacing: -1px;
    }

    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.15rem;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
    }

    /* Status Badge */
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.9rem;
        margin-top: 1rem;
    }

    .status-online {
        background: rgba(16, 185, 129, 0.2);
        color: var(--success);
        border: 1px solid var(--success);
    }

    .status-offline {
        background: rgba(239, 68, 68, 0.2);
        color: var(--danger);
        border: 1px solid var(--danger);
    }

    /* Card Components */
    .metric-card {
        background: var(--bg-card);
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
        border-color: var(--primary);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
    }

    .metric-label {
        color: var(--text-muted);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    /* Content Section */
    .content-section {
        background: var(--bg-card);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }

    .content-section h3 {
        color: var(--text-light);
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 1rem;
    }

    /* Article Cards */
    .article-card {
        background: rgba(30, 41, 59, 0.6);
        padding: 1.25rem;
        border-radius: 12px;
        border-left: 4px solid var(--primary);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .article-card:hover {
        background: rgba(30, 41, 59, 0.9);
        border-left-color: var(--accent);
        transform: translateX(4px);
    }

    .article-title {
        color: var(--text-light);
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .article-meta {
        color: var(--text-muted);
        font-size: 0.85rem;
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .article-source {
        background: rgba(99, 102, 241, 0.2);
        padding: 0.25rem 0.75rem;
        border-radius: 50px;
        font-size: 0.8rem;
        color: var(--primary);
        font-weight: 600;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 12px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.6);
    }

    /* Sidebar */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: var(--bg-card);
        border-right: 1px solid var(--border);
    }

    /* Progress Bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--primary), var(--secondary));
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        color: var(--text-muted);
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        color: white;
        border-color: transparent;
    }

    /* Markdown Content */
    .content-section p, .content-section li {
        color: var(--text-light);
        line-height: 1.7;
    }

    .content-section a {
        color: var(--primary);
        text-decoration: none;
        font-weight: 600;
        transition: color 0.3s ease;
    }

    .content-section a:hover {
        color: var(--secondary);
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: var(--text-muted);
        font-size: 0.9rem;
        border-top: 1px solid var(--border);
        margin-top: 3rem;
    }

    /* Loading Animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .loading {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary);
    }
</style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================

if 'final_briefing' not in st.session_state:
    st.session_state.final_briefing = None
if 'articles' not in st.session_state:
    st.session_state.articles = []
if 'run_timestamp' not in st.session_state:
    st.session_state.run_timestamp = None
if 'selected_profile' not in st.session_state:
    st.session_state.selected_profile = 'balanced'
if 'max_articles' not in st.session_state:
    st.session_state.max_articles = 50

# ==================== HEADER ====================

st.markdown("""
<div class="main-header">
    <h1>🤖 AI Intelligence Hub</h1>
    <p>Real-time AI news aggregation from 40+ premium sources</p>
    <span class="status-badge status-online">● LIVE</span>
</div>
""", unsafe_allow_html=True)

# ==================== SIDEBAR ====================

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # Source Profile Selection
    profile = st.selectbox(
        "Source Profile",
        options=list(PROFILE_MAP.keys()) if IMPORTS_OK else ['balanced'],
        index=0,
        help="Select which sources to fetch from"
    )
    st.session_state.selected_profile = profile

    # Show source count
    if IMPORTS_OK:
        source_count = get_active_sources_count(profile)
        st.info(f"**{source_count}** active sources in this profile")

    # Article limit
    st.session_state.max_articles = st.slider(
        "Max Articles",
        min_value=10,
        max_value=200,
        value=st.session_state.max_articles,
        step=10,
        help="Maximum number of articles to fetch"
    )

    st.markdown("---")

    # Features
    st.markdown("### 🎛️ Features")

    enable_realtime = st.checkbox(
        "Real-time Search",
        value=True,
        help="Include real-time search results from DuckDuckGo"
    )

    enable_audio = st.checkbox(
        "Audio Briefing",
        value=False,
        help="Generate text-to-speech audio"
    )

    enable_analysis = st.checkbox(
        "Detailed Analysis",
        value=False,
        help="Include extended analysis and insights"
    )

    st.markdown("---")

    # Source Categories
    if IMPORTS_OK:
        st.markdown("### 📊 Source Categories")
        categories = get_sources_by_category(profile)
        for category, sources in categories.items():
            st.metric(category.title(), len(sources))

    st.markdown("---")

    # Cache Management
    st.markdown("### 🗄️ Cache")
    if st.button("Clear Cache"):
        cache_dir = Path('.cache/news')
        if cache_dir.exists():
            count = 0
            for f in cache_dir.glob('*.json'):
                f.unlink()
                count += 1
            st.success(f"Cleared {count} cache files!")

    # Update timestamp
    if st.session_state.run_timestamp:
        st.caption(f"Last updated: {st.session_state.run_timestamp}")

# ==================== MAIN CONTENT ====================

# Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    source_count = get_active_sources_count(profile) if IMPORTS_OK else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Sources</div>
        <div class="metric-value">{source_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    article_count = len(st.session_state.articles)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Articles Found</div>
        <div class="metric-value">{article_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    categories_count = len(get_sources_by_category(profile)) if IMPORTS_OK else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Categories</div>
        <div class="metric-value">{categories_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    status = "Online" if IMPORTS_OK else "Offline"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Status</div>
        <div class="metric-value">{'✓' if IMPORTS_OK else '✗'}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Action Button
col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

with col_btn1:
    if st.button("🚀 Generate AI News Briefing", use_container_width=True):
        if not IMPORTS_OK:
            st.error("Required modules not imported. Check installation.")
        else:
            with st.spinner(""):
                try:
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Step 1: Fetch articles
                    status_text.markdown("**Step 1/4:** Fetching articles from sources...")
                    progress_bar.progress(10)

                    os.environ['ENABLE_REALTIME_SEARCH'] = 'true' if enable_realtime else 'false'
                    articles = fetch_recent_articles(
                        profile=profile,
                        max_articles=st.session_state.max_articles
                    )
                    st.session_state.articles = articles
                    progress_bar.progress(40)

                    # Step 2: Process with AI
                    status_text.markdown("**Step 2/4:** Analyzing with AI agents...")
                    time.sleep(0.5)
                    progress_bar.progress(60)

                    briefing = run_crew()
                    progress_bar.progress(80)

                    # Step 3: Generate audio (if enabled)
                    if enable_audio:
                        status_text.markdown("**Step 3/4:** Generating audio briefing...")
                        # Audio generation would happen here
                    progress_bar.progress(90)

                    # Step 4: Finalize
                    status_text.markdown("**Step 4/4:** Finalizing...")
                    st.session_state.final_briefing = briefing
                    st.session_state.run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    progress_bar.progress(100)
                    time.sleep(0.5)

                    status_text.empty()
                    progress_bar.empty()
                    st.success("✅ Briefing generated successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

with col_btn2:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.session_state.articles = []
        st.session_state.final_briefing = None
        st.rerun()

with col_btn3:
    if st.session_state.final_briefing:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "📥 Export",
            data=st.session_state.final_briefing,
            file_name=f"ai_briefing_{timestamp}.md",
            mime="text/markdown",
            use_container_width=True
        )

# ==================== BRIEFING OUTPUT ====================

if st.session_state.final_briefing:

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Briefing", "📰 All Sources", "📊 Analytics", "🔊 Audio"])

    with tab1:
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown(st.session_state.final_briefing)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown("### All Fetched Articles")

        if st.session_state.articles:
            # Group by source
            sources_dict = {}
            for article in st.session_state.articles:
                source = article.get('source', 'Unknown')
                if source not in sources_dict:
                    sources_dict[source] = []
                sources_dict[source].append(article)

            # Display by source
            for source, arts in sorted(sources_dict.items()):
                with st.expander(f"**{source}** ({len(arts)} articles)"):
                    for article in arts:
                        st.markdown(f"""
                        <div class="article-card">
                            <div class="article-title">{article.get('title', 'No title')}</div>
                            <div class="article-meta">
                                <span class="article-source">{article.get('source_type', 'N/A')}</span>
                                <span>📅 {article.get('published', 'N/A')[:10]}</span>
                                <span><a href="{article.get('link', '#')}" target="_blank">🔗 Read more</a></span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("No articles fetched yet. Click 'Generate Briefing' to start.")

        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown("### Analytics Dashboard")

        if st.session_state.articles:
            # Source type distribution
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Articles by Source Type")
                source_types = {}
                for article in st.session_state.articles:
                    stype = article.get('source_type', 'unknown')
                    source_types[stype] = source_types.get(stype, 0) + 1

                for stype, count in sorted(source_types.items(), key=lambda x: x[1], reverse=True):
                    st.metric(stype.replace('_', ' ').title(), count)

            with col2:
                st.markdown("#### Top Sources")
                sources_count = {}
                for article in st.session_state.articles:
                    source = article.get('source', 'Unknown')
                    sources_count[source] = sources_count.get(source, 0) + 1

                for source, count in sorted(sources_count.items(), key=lambda x: x[1], reverse=True)[:10]:
                    st.metric(source, count)

            # Timeline
            st.markdown("#### Publication Timeline")
            timeline_data = {}
            for article in st.session_state.articles:
                try:
                    pub_date = article.get('published', '')[:10]
                    timeline_data[pub_date] = timeline_data.get(pub_date, 0) + 1
                except:
                    pass

            if timeline_data:
                st.bar_chart(timeline_data)
        else:
            st.info("Generate a briefing to see analytics.")

        st.markdown('</div>', unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="content-section">', unsafe_allow_html=True)

        if enable_audio:
            st.markdown("### 🔊 Audio Briefing")

            try:
                audio_path = generate_audio_briefing(st.session_state.final_briefing)
                if audio_path and Path(audio_path).exists():
                    with open(audio_path, 'rb') as f:
                        audio_bytes = f.read()
                    st.audio(audio_bytes, format='audio/mp3')

                    st.download_button(
                        "📥 Download Audio",
                        data=audio_bytes,
                        file_name=f"ai_briefing_{datetime.now().strftime('%Y%m%d')}.mp3",
                        mime="audio/mp3"
                    )
                else:
                    st.error("Audio generation failed.")
            except Exception as e:
                st.error(f"Audio error: {str(e)}")
        else:
            st.info("Enable 'Audio Briefing' in the sidebar to generate spoken version.")

        st.markdown('</div>', unsafe_allow_html=True)

else:
    # No briefing yet
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown("### Welcome to AI Intelligence Hub")
    st.markdown("""
    This advanced AI news aggregation system pulls real-time news from **40+ premium sources** including:

    - **Academic**: arXiv, MIT News, Stanford HAI, Berkeley AI Research
    - **Industry**: OpenAI, DeepMind, Anthropic, Meta AI, Microsoft, Google
    - **Tech News**: TechCrunch, VentureBeat, MIT Tech Review, Wired
    - **Community**: Hacker News, Reddit ML, AI Weekly
    - **Real-time Search**: DuckDuckGo News API

    **Click the button above to generate your first briefing!**
    """)
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== FOOTER ====================

st.markdown(f"""
<div class="footer">
    AI Intelligence Hub v2.0 | Powered by CrewAI & Streamlit<br>
    Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
</div>
""", unsafe_allow_html=True)