# file: app.py
import streamlit as st
from agent_crew import run_crew, recent_articles_list
from audio_generator import generate_audio_briefing
import os
from datetime import datetime
import time
import requests

# ---------- Page Config ----------
st.set_page_config(page_title="AI Intelligence Agent", page_icon="🤖", layout="wide")

# ---------- Connectivity ----------
def check_connectivity() -> bool:
    try:
        requests.get("https://www.google.com", timeout=4)
        return True
    except Exception:
        return False

# ---------- Fallback ----------
def fallback_briefing() -> str:
    ts = datetime.now().strftime("%B %d, %Y")
    count = len(recent_articles_list) if recent_articles_list else 0
    return f"""### Offline Briefing ({ts})\n\nConnectivity unavailable. {count} cached article(s) detected.\n\nRe-run when online for full AI analysis."""

# ---------- Styles (clean + minimal) ----------
st.markdown("""
<style>
    :root { --brand:#1f5eff; --border:#eceef1; --bg-soft:#f6f8fa; }
    .main-header { margin: .25rem 0 1rem 0; }
    .main-header h1 { font-size:2.05rem; margin:0 0 .35rem; font-weight:650; letter-spacing:.5px; }
    .main-header p { margin:0; color:#555; font-size:.9rem; }
    .chipbar { display:flex; gap:.5rem; flex-wrap:wrap; margin-bottom:1rem; }
    .chip { background:var(--bg-soft); border:1px solid var(--border); padding:.35rem .65rem; border-radius:6px; font-size:.68rem; letter-spacing:.5px; font-weight:600; text-transform:uppercase; color:#444; }
    .primary button { background:var(--brand) !important; border:none; font-weight:600; padding:.85rem 1.1rem; border-radius:9px; }
    .primary button:disabled { opacity:.45; filter:grayscale(.3); }
    .section { background:#fff; border:1px solid var(--border); padding:1.1rem 1.15rem; border-radius:10px; }
    .sources-item { font-size:.8rem; padding:.4rem .2rem; border-bottom:1px solid #f0f1f3; }
    .sources-item:last-child { border-bottom:none; }
    .status-dot { width:10px; height:10px; border-radius:50%; display:inline-block; margin-right:6px; position:relative; top:1px; }
    .online { background:#1abc9c; }
    .offline { background:#e74c3c; }
    .footer { text-align:center; font-size:.7rem; color:#888; margin:2.2rem 0 1rem; }
    .stTabs [data-baseweb="tab-list"] { gap:.4rem; }
    .stTabs [data-baseweb="tab"] { background:#f2f4f6; border-radius:7px; padding:.35rem .75rem; font-size:.75rem; }
    .stTabs [aria-selected="true"] { background:var(--brand); color:#fff; }
    .warn-box { background:#fff7e6; border:1px solid #ffe2b3; padding:.7rem .9rem; border-radius:8px; font-size:.8rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Session State (no default-enabled features) ----------
_defaults = {
    "show_detailed_analysis": False,
    "include_trending_topics": False,
    "audio_enabled": False,
    "allow_fallback": True,
    "final_briefing": None,
    "run_timestamp": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

is_online = check_connectivity()
article_count = len(recent_articles_list) if recent_articles_list else 0

# ---------- Sidebar ----------
with st.sidebar:
    st.subheader("AI News")
    st.caption("Minimal daily intelligence")
    dot = f"<span class='status-dot {'online' if is_online else 'offline'}'></span>"
    st.markdown(f"**Status:** {dot}{'Online' if is_online else 'Offline'}", unsafe_allow_html=True)
    st.markdown(f"**Articles:** {article_count}")
    st.divider()
    with st.expander("Options", expanded=False):
        st.session_state.show_detailed_analysis = st.checkbox("Detailed analysis", value=st.session_state.show_detailed_analysis)
        st.session_state.include_trending_topics = st.checkbox("Trending topics", value=st.session_state.include_trending_topics)
        st.session_state.audio_enabled = st.checkbox("Audio output", value=st.session_state.audio_enabled)
        st.session_state.allow_fallback = st.checkbox("Allow offline fallback", value=st.session_state.allow_fallback)
    st.divider()
    if st.button("Reset", use_container_width=True):
        for k in ["final_briefing", "run_timestamp"]:
            st.session_state[k] = None
        st.toast("Reset complete", icon="✅")

# ---------- Header ----------
st.markdown("""
<div class='main-header'>
  <h1>AI News Briefing</h1>
  <p>Concise coverage. Enable only what you need.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Chip Bar ----------
chips = [f"Articles: {article_count}"]
if st.session_state.run_timestamp:
    chips.append(f"Last: {st.session_state.run_timestamp.split(' ')[1]}")
chips.append("Mode: Online" if is_online else "Mode: Offline")
st.markdown("<div class='chipbar'>" + "".join(f"<span class='chip'>{c}</span>" for c in chips) + "</div>", unsafe_allow_html=True)

# ---------- Action ----------
col_a, col_b, col_c = st.columns([1,2,1])
with col_b:
    disabled = (not is_online and not st.session_state.allow_fallback) or (article_count == 0 and is_online)
    label = "Generate Briefing" if is_online else ("Offline Fallback" if st.session_state.allow_fallback else "Retry (Need Online)")
    run_clicked = st.button(label, key="run_btn", type="primary", disabled=disabled, use_container_width=True)

    if run_clicked:
        prog = st.progress(0)
        phase = st.empty()
        try:
            if is_online:
                for pct, msg in [(12,"Collecting sources"),(34,"Filtering & ranking"),(55,"Summarizing"),(72,"Refining"),(90,"Formatting")]:
                    phase.info(msg)
                    prog.progress(pct)
                    time.sleep(0.12)
                briefing = run_crew()
            else:
                phase.warning("Offline fallback mode")
                prog.progress(45)
                time.sleep(0.25)
                briefing = fallback_briefing()
                prog.progress(85)
            prog.progress(100)
            phase.success("Complete")
            st.session_state.final_briefing = briefing
            st.session_state.run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time.sleep(.25)
            phase.empty(); prog.empty()
        except Exception as e:
            phase.error("Failed")
            prog.empty()
            st.error(f"Error: {e}")
            if any(x in str(e).lower() for x in ["getaddrinfo", "connection", "apiconnectionerror"]):
                st.info("Connectivity issue detected.")

# ---------- Output ----------
if st.session_state.final_briefing:
    st.markdown("<div class='section'>", unsafe_allow_html=True)
    st.markdown("#### Briefing")
    st.markdown(st.session_state.final_briefing)
    st.markdown("</div>", unsafe_allow_html=True)

    tab_sources, tab_analysis, tab_audio = st.tabs(["Sources", "Analysis", "Audio"])

    with tab_sources:
        if recent_articles_list:
            for i, art in enumerate(recent_articles_list[:15], 1):
                title = art.get('title', '(untitled)')
                link = art.get('link', '#')
                st.markdown(f"<div class='sources-item'><strong>{i}.</strong> <a href='{link}' target='_blank'>{title}</a></div>", unsafe_allow_html=True)
        else:
            st.caption("No sources available.")

    with tab_analysis:
        if st.session_state.show_detailed_analysis and is_online:
            st.markdown("**(Planned extension)** Deeper entity / sentiment / thematic momentum metrics.")
        elif st.session_state.show_detailed_analysis and not is_online:
            st.info("Detailed analysis requires online mode.")
        else:
            st.caption("Enable 'Detailed analysis' in options to include extended insights.")
        if st.session_state.include_trending_topics and is_online:
            st.divider()
            st.markdown("**Trending Topics (sample)**")
            st.code("['multi-modal reasoning', 'agent frameworks', 'parameter-efficient training']")
        elif st.session_state.include_trending_topics and not is_online:
            st.info("Trending topics unavailable offline.")

    with tab_audio:
        if st.session_state.audio_enabled:
            if is_online:
                with st.spinner("Synthesizing audio..."):
                    try:
                        path = generate_audio_briefing(st.session_state.final_briefing)
                        if path and os.path.exists(path):
                            with open(path, 'rb') as f: data = f.read()
                            st.audio(data, format='audio/mp3')
                            st.download_button("Download MP3", data=data, file_name=f"briefing_{datetime.now().strftime('%Y%m%d')}.mp3", mime='audio/mp3')
                        else:
                            st.error("Audio generation failed.")
                    except Exception as e:
                        st.error(f"Audio error: {e}")
            else:
                st.info("Audio requires online mode.")
        else:
            st.caption("Enable 'Audio output' to synthesize a spoken version.")
else:
    st.markdown("<div class='section'>", unsafe_allow_html=True)
    if article_count == 0 and is_online:
        st.info("No recent articles yet. Try again later or adjust sources.")
    else:
        st.caption("Click 'Generate Briefing' to start. Optional features are off by default.")
    if not is_online and st.session_state.allow_fallback:
        st.markdown("<div class='warn-box'>Offline fallback available – you can still generate a cached summary.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown(f"<div class='footer'>© AI News Agent • Updated {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
