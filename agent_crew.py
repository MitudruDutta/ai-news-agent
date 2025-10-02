# file: agent_crew.py
"""
Enhanced AI Agent Crew for News Analysis
Dynamic source integration, intelligent analysis, and comprehensive summarization
"""

from __future__ import annotations

from typing import Any
from dotenv import load_dotenv
import os, json
from datetime import datetime

load_dotenv()

# ==================== GEMINI-ONLY CONFIG ====================
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

DEFAULT_MODEL = "gemini-2.5-flash" if GEMINI_KEY else None
DEFAULT_PROVIDER = "gemini" if GEMINI_KEY else "none"
print(f"🔧 LLM Provider: {DEFAULT_PROVIDER} | Model: {DEFAULT_MODEL}")
print(f"🔑 API Key Status: {'✓ Found' if GEMINI_KEY else '❌ Missing'}")

# Expose for downstream libs
if GEMINI_KEY:
    os.environ['GOOGLE_API_KEY'] = GEMINI_KEY
    # Use the correct format for litellm
    os.environ['CREWAI_LLM_MODEL'] = "gemini/gemini-2.5-flash"
    os.environ['CREWAI_LLM_PROVIDER'] = 'gemini'


# Disable CrewAI memory features explicitly to avoid embedding requirements
os.environ['CREWAI_DISABLE_MEMORY'] = 'true'
os.environ['CHROMA_TELEMETRY'] = 'False'

# ==================== CREWAI IMPORTS (Gemini only) ====================
CREW_AVAILABLE = True
try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import tool
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        class ChatGoogleGenerativeAI:  # type: ignore
            def __init__(self, *args, **kwargs):
                pass
except ImportError:
    CREW_AVAILABLE = False
    print("⚠️ CrewAI not available. Using fallback mode.")
    class Agent:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
    class Task:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
    class Crew:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
        def kickoff(self, *args, **kwargs):
            return ""
    class Process:  # type: ignore
        sequential = "sequential"
    def tool(name: str):  # type: ignore
        def wrapper(fn): return fn
        return wrapper

# ==================== SOURCE INTEGRATION ====================
try:
    from sources_config import get_sources_by_profile
    from news_fetcher import fetch_recent_articles, extract_article_text
except ImportError:
    def get_sources_by_profile(profile='balanced'): return {}
    def fetch_recent_articles(profile='balanced', max_articles=50): return []
    def extract_article_text(url: str): return ""

FEED_PROFILE = os.getenv("FEED_PROFILE", "balanced").lower()
MAX_ARTICLES_TO_ANALYZE = int(os.getenv("MAX_ARTICLES_TO_ANALYZE", "30"))
TOP_STORIES_COUNT = int(os.getenv("TOP_STORIES_COUNT", "5"))

recent_articles_list: list[dict] = []

# ==================== TOOL ====================
@tool("Article Text Fetcher")
def fetch_article_text_tool(url: str) -> str:
    """Fetch and return up to 5000 chars of article text for a URL (Gemini-only stack)."""
    try:
        text = extract_article_text(url)
        return text[:5000] if text else "Article text extraction failed or empty."
    except Exception as e:
        return f"Error fetching article: {e}"

# ==================== LLM (Gemini only) ====================
llm_instance = None
if CREW_AVAILABLE and DEFAULT_MODEL and GEMINI_KEY:
    try:
        # Correctly instantiate the ChatGoogleGenerativeAI class
        llm_instance = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, temperature=0.7)
        print(f"✓ Successfully initialized Gemini model: {DEFAULT_MODEL}")
    except Exception as e:
        print(f"⚠️ Gemini initialization failed: {e}")
        llm_instance = None
else:
    if not GEMINI_KEY:
        print("⚠️ No GEMINI_API_KEY provided. Falling back to basic briefing.")

# ==================== AGENTS (memory disabled) ====================
if CREW_AVAILABLE and llm_instance:
    researcher = Agent(
        role='Senior AI News Researcher',
        goal='Extract and compile comprehensive information from AI news articles',
        backstory='Expert AI researcher focusing on rapid extraction of key insights from diverse AI sources.',
        verbose=True,
        allow_delegation=False,
        llm=llm_instance,
        max_iter=3,
        memory=False
    )
    analyst = Agent(
        role='Principal AI News Analyst',
        goal=f'Identify and rank the top {TOP_STORIES_COUNT} impactful AI stories',
        backstory='Seasoned AI industry analyst prioritizing genuine impact over hype.',
        verbose=True,
        allow_delegation=False,
        llm=llm_instance,
        max_iter=3,
        memory=False
    )
    summarizer = Agent(
        role='Executive AI Briefing Writer',
        goal='Produce a clear, actionable executive AI news briefing',
        backstory='Skilled technical communicator translating complex developments into concise insights.',
        verbose=True,
        allow_delegation=False,
        llm=llm_instance,
        max_iter=3,
        memory=False
    )
else:
    researcher = analyst = summarizer = None

news_crew = None  # built per run

# ==================== FALLBACK BRIEFING ====================
from datetime import datetime

def generate_fallback_briefing() -> str:
    lines = [
        "# Daily AI Intelligence Briefing",
        f"\n**Date:** {datetime.now().strftime('%B %d, %Y')}",
        f"**Status:** Fallback Mode (Gemini model unavailable)",
        f"**Articles Processed:** {len(recent_articles_list)}",
        "\n## Recent AI News\n"
    ]
    for article in recent_articles_list[:15]:
        title = article.get('title','Untitled')
        src = article.get('source','Unknown')
        link = article.get('link','#')
        summary = (article.get('summary') or '')[:220]
        lines.append(f"### {title}\n*Source:* {src}\n{summary}...\n[Read more]({link})\n")
    lines.append("---\n*Provide a GEMINI_API_KEY to enable AI analysis.*")
    return "\n".join(lines)

# ==================== RESULT COERCION ====================
import json as _json

def process_crew_result(result: Any) -> str:
    if result is None:
        return generate_fallback_briefing()
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for k in ('final_output','output','result','content','text'):
            v = result.get(k)
            if isinstance(v,str) and v.strip():
                return v
        try:
            return _json.dumps(result, indent=2, ensure_ascii=False)
        except Exception:
            return str(result)
    for attr in ('final_output','output','raw','result'):
        if hasattr(result, attr):
            v = getattr(result, attr)
            if isinstance(v,str) and v.strip():
                return v
    return str(result)

# ==================== CONTEXT BUILD ====================

def _build_context(articles: list[dict]) -> tuple[str, list[dict]]:
    subset = []
    for a in articles[:MAX_ARTICLES_TO_ANALYZE]:
        if len(subset) >= 20: break
        subset.append(a)
    ctx = "\n\n".join([
        f"Article {i+1}:\nTitle: {a.get('title','N/A')}\nSource: {a.get('source','N/A')}\nLink: {a.get('link','N/A')}\nPublished: {a.get('published','N/A')}\nSummary: {(a.get('summary') or '')[:300]}" for i,a in enumerate(subset)
    ])
    return ctx, subset

# ==================== EXECUTION ====================

def run_crew() -> str:
    global recent_articles_list, news_crew
    print("\n" + "="*60) ; print("🚀 EXECUTING AI NEWS CREW") ; print("="*60)
    if not recent_articles_list:
        try:
            print(f"📡 Fetching articles (profile={FEED_PROFILE})...")
            recent_articles_list = fetch_recent_articles(profile=FEED_PROFILE, max_articles=MAX_ARTICLES_TO_ANALYZE)
            print(f"✅ Retrieved {len(recent_articles_list)} articles")
        except Exception as e:
            print(f"❌ Fetch failure: {e}")
            return generate_fallback_briefing()
    if not recent_articles_list:
        return generate_fallback_briefing()
    if not (CREW_AVAILABLE and llm_instance and researcher and analyst and summarizer):
        print("⚠️ Gemini LLM unavailable -> fallback.")
        return generate_fallback_briefing()
    try:
        ctx_str, subset = _build_context(recent_articles_list)
        task_research = Task(
            description=(f"Analyze {len(subset)} AI news articles. Use the Article Text Fetcher tool for up to 10 promising pieces. Provide structured JSON of key findings.\n\nARTICLES:\n\n" + ctx_str),
            expected_output="JSON array with: title, link, source, published, key_findings, technical_details, metrics, implications, relevance_score (1-10)",
            agent=researcher,
            tools=[fetch_article_text_tool]
        )
        task_analyze = Task(
            description=(f"Select top {TOP_STORIES_COUNT} impactful stories from research output with rationale and diversity summary."),
            expected_output="JSON with selected, rationale, diversity_analysis, criteria_summary",
            agent=analyst,
            context=[task_research]
        )
        task_summarize = Task(
            description="Produce executive markdown briefing (Header, Date, Executive Summary, Top Stories, Trends & Insights, Looking Ahead).",
            expected_output="Polished markdown briefing (≈800-1200 words) actionable",
            agent=summarizer,
            context=[task_analyze]
        )
        news_crew = Crew(
            agents=[researcher, analyst, summarizer],
            tasks=[task_research, task_analyze, task_summarize],
            process=Process.sequential,
            verbose=True,
            memory=False,
            full_output=True,
            llm=llm_instance
        )
        print("🤖 Running agents...")
        result = news_crew.kickoff(inputs={'top_stories_count': TOP_STORIES_COUNT})
        briefing = process_crew_result(result)
        if not briefing or len(briefing) < 120:
            print("⚠️ Insufficient output -> fallback.")
            return generate_fallback_briefing()
        if 'Daily AI' not in briefing:
            briefing = f"# Daily AI Intelligence Briefing\n\n{briefing}"
        print(f"📝 Briefing length: {len(briefing)} chars")
        return briefing
    except Exception as e:
        print(f"❌ Crew execution error: {e}")
        return generate_fallback_briefing()

# ==================== STANDALONE ====================
if __name__ == '__main__':
    print("\n=== AI NEWS AGENT - STANDALONE (Gemini Only) ===")
    print(f"Model: {DEFAULT_MODEL} | Provider: {DEFAULT_PROVIDER}")
    briefing = run_crew()
    print("\n=== FINAL BRIEFING ===\n")
    print(briefing)
    out_file = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    try:
        with open(out_file, 'w', encoding='utf-8') as f: f.write(briefing)
        print(f"Saved to {out_file}")
    except Exception as e:
        print(f"Save failed: {e}")
