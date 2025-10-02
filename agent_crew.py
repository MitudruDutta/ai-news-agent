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

# ==================== HELPER FUNCTION ====================
def get_env_clean(key: str, default: str = "") -> str:
    """Get environment variable and strip quotes if present"""
    value = os.getenv(key, default)
    if value and isinstance(value, str):
        value = value.strip("'\"")
    return value

# ==================== DISABLE TELEMETRY ====================
os.environ['CREWAI_TELEMETRY_OPT_OUT'] = 'true'  # Disable CrewAI telemetry
os.environ['CREWAI_DISABLE_TELEMETRY'] = 'true'
os.environ['OTEL_SDK_DISABLED'] = 'true'

# ==================== GEMINI-ONLY CONFIG ====================
GEMINI_KEY = get_env_clean("GEMINI_API_KEY") or get_env_clean("GOOGLE_API_KEY")

# Use a stable Gemini model - just the model name without prefix for ChatGoogleGenerativeAI
DEFAULT_MODEL = "gemini-2.0-flash-exp"  # FIXED: ChatGoogleGenerativeAI adds its own prefix
DEFAULT_PROVIDER = "gemini" if GEMINI_KEY else "none"

print(f"🔧 LLM Provider: {DEFAULT_PROVIDER} | Model: {DEFAULT_MODEL}")

# Expose for downstream libs
if GEMINI_KEY:
    os.environ['GOOGLE_API_KEY'] = GEMINI_KEY

# Disable CrewAI memory features explicitly
os.environ['CREWAI_DISABLE_MEMORY'] = 'true'
os.environ['CHROMA_TELEMETRY'] = 'False'

# ==================== CREWAI IMPORTS ====================
CREW_AVAILABLE = True
try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import tool
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("✓ langchain_google_genai imported successfully")
    except ImportError as e:
        print(f"⚠️ langchain_google_genai import failed: {e}")
        class ChatGoogleGenerativeAI:
            def __init__(self, *args, **kwargs):
                pass
except ImportError as e:
    CREW_AVAILABLE = False
    print(f"⚠️ CrewAI not available: {e}")
    class Agent:
        def __init__(self, *args, **kwargs):
            pass
    class Task:
        def __init__(self, *args, **kwargs):
            pass
    class Crew:
        def __init__(self, *args, **kwargs):
            pass
        def kickoff(self, *args, **kwargs):
            return ""
    class Process:
        sequential = "sequential"
    def tool(name: str):
        def wrapper(fn): return fn
        return wrapper

# ==================== SOURCE INTEGRATION ====================
try:
    from sources_config import get_sources_by_profile
    from news_fetcher import fetch_recent_articles, extract_article_text
    print("✓ Successfully imported news_fetcher and sources_config")
except ImportError as e:
    print(f"⚠️ Import error: {e}")
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
    """Fetch and return up to 5000 chars of article text for a URL"""
    try:
        text = extract_article_text(url)
        return text[:5000] if text else "Article text extraction failed or empty."
    except Exception as e:
        return f"Error fetching article: {e}"

# ==================== LLM INITIALIZATION ====================
# CrewAI uses litellm internally, so we need to configure it properly
llm_instance = None
if CREW_AVAILABLE and GEMINI_KEY:
    try:
        from crewai import LLM
        
        # Use CrewAI's LLM wrapper with proper litellm format
        llm_instance = LLM(
            model="gemini/gemini-2.0-flash-exp",
            temperature=0.7,
            api_key=GEMINI_KEY
        )
        print(f"✓ Successfully initialized Gemini model via CrewAI LLM: gemini/gemini-2.0-flash-exp")
    except Exception as e:
        print(f"⚠️ Gemini initialization failed: {e}")
        # Fallback to ChatGoogleGenerativeAI if CrewAI LLM fails
        try:
            llm_instance = ChatGoogleGenerativeAI(
                model=DEFAULT_MODEL,
                temperature=0.7,
                google_api_key=GEMINI_KEY,
                convert_system_message_to_human=True,
                timeout=60
            )
            print(f"✓ Fallback to ChatGoogleGenerativeAI: {DEFAULT_MODEL}")
        except Exception as e2:
            print(f"⚠️ All LLM initialization methods failed: {e2}")
            llm_instance = None
else:
    if not GEMINI_KEY:
        print("⚠️ No GEMINI_API_KEY provided. Falling back to basic briefing.")

# ==================== AGENTS ====================
if CREW_AVAILABLE and llm_instance:
    researcher = Agent(
        role='Senior AI News Researcher',
        goal='Extract and compile comprehensive information from AI news articles',
        backstory='Expert AI researcher focusing on rapid extraction of key insights from diverse AI sources.',
        verbose=True,
        allow_delegation=False,
        llm=llm_instance,
        max_iter=5,
        memory=False
    )
    analyst = Agent(
        role='Principal AI News Analyst',
        goal=f'Identify and rank the top {TOP_STORIES_COUNT} impactful AI stories',
        backstory='Seasoned AI industry analyst prioritizing genuine impact over hype.',
        verbose=True,
        allow_delegation=False,
        llm=llm_instance,
        max_iter=5,
        memory=False
    )
    summarizer = Agent(
        role='Executive AI Briefing Writer',
        goal='Produce a clear, actionable executive AI news briefing',
        backstory='Skilled technical communicator translating complex developments into concise insights.',
        verbose=True,
        allow_delegation=False,
        llm=llm_instance,
        max_iter=5,
        memory=False
    )
else:
    researcher = analyst = summarizer = None

news_crew = None

# ==================== FALLBACK BRIEFING ====================
def generate_fallback_briefing() -> str:
    """Generate comprehensive fallback briefing when AI is unavailable"""
    lines = [
        "# 🤖 Daily AI Intelligence Briefing",
        f"\n**Date:** {datetime.now().strftime('%B %d, %Y')}",
        f"**Status:** Fallback Mode (AI analysis unavailable)",
        f"**Articles Processed:** {len(recent_articles_list)}",
        "\n---\n",
        "\n## 📰 Recent AI News\n"
    ]

    for i, article in enumerate(recent_articles_list[:50], 1):
        title = article.get('title', 'Untitled')
        src = article.get('source', 'Unknown')
        link = article.get('url') or article.get('link', '#')
        published = article.get('published', 'N/A')
        summary = (article.get('description') or article.get('summary') or '')[:300]

        lines.append(f"### {i}. {title}\n")
        lines.append(f"**Source:** {src} | **Published:** {published}\n")
        if summary:
            lines.append(f"{summary}...\n")
        lines.append(f"[Read full article]({link})\n\n")

    lines.append("\n---\n")
    lines.append("*💡 Tip: Add a valid GEMINI_API_KEY to enable AI-powered analysis.*")
    lines.append(f"\n*Total articles: {len(recent_articles_list)}*")

    return "\n".join(lines)

# ==================== RESULT PROCESSING ====================
def process_crew_result(result: Any) -> str:
    """Process and extract string output from CrewAI result"""
    if result is None:
        return generate_fallback_briefing()
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for k in ('final_output', 'output', 'result', 'content', 'text', 'raw'):
            v = result.get(k)
            if isinstance(v, str) and v.strip():
                return v
        try:
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception:
            return str(result)

    for attr in ('final_output', 'output', 'raw', 'result', 'text'):
        if hasattr(result, attr):
            v = getattr(result, attr)
            if isinstance(v, str) and v.strip():
                return v

    return str(result)

# ==================== CONTEXT BUILD ====================
def _build_context(articles: list[dict]) -> tuple[str, list[dict]]:
    """Build context string from articles"""
    subset = articles[:min(len(articles), MAX_ARTICLES_TO_ANALYZE)]

    ctx_parts = []
    for i, a in enumerate(subset, 1):
        title = a.get('title', 'N/A')
        source = a.get('source', 'N/A')
        link = a.get('url') or a.get('link', 'N/A')
        published = a.get('published', 'N/A')
        summary = (a.get('description') or a.get('summary') or '')[:400]

        ctx_parts.append(
            f"Article {i}:\nTitle: {title}\nSource: {source}\n"
            f"Link: {link}\nPublished: {published}\nSummary: {summary}\n"
        )

    return "\n\n".join(ctx_parts), subset

# ==================== EXECUTION ====================
def run_crew() -> str:
    """Main execution function for the AI news crew"""
    global recent_articles_list, news_crew

    print("\n" + "="*80)
    print("🚀 EXECUTING AI NEWS CREW")
    print("="*80)

    if not recent_articles_list:
        try:
            print(f"📡 Fetching articles (profile={FEED_PROFILE})...")
            recent_articles_list = fetch_recent_articles(
                profile=FEED_PROFILE,
                max_articles=int(os.getenv("MAX_ARTICLES", "100"))
            )
            print(f"✅ Retrieved {len(recent_articles_list)} articles")
        except Exception as e:
            print(f"❌ Fetch failure: {e}")
            import traceback
            traceback.print_exc()
            return generate_fallback_briefing()

    if not recent_articles_list:
        print("⚠️ No articles found")
        return generate_fallback_briefing()

    if not (CREW_AVAILABLE and llm_instance and researcher and analyst and summarizer):
        print("⚠️ Gemini LLM unavailable -> using fallback mode")
        return generate_fallback_briefing()

    try:
        print(f"📊 Building context from {len(recent_articles_list)} articles...")
        ctx_str, subset = _build_context(recent_articles_list)
        print(f"✓ Context built: {len(subset)} articles, {len(ctx_str)} chars")

        task_research = Task(
            description=(
                f"Analyze these {len(subset)} AI news articles. "
                f"Extract key findings, technical details, and implications.\n\n"
                f"ARTICLES:\n\n{ctx_str}\n\n"
                f"Provide structured analysis."
            ),
            expected_output="Detailed analysis of articles with key findings.",
            agent=researcher,
            tools=[fetch_article_text_tool]
        )

        task_analyze = Task(
            description=f"Select the top {TOP_STORIES_COUNT} most impactful stories.",
            expected_output=f"Top {TOP_STORIES_COUNT} stories with rationale.",
            agent=analyst,
            context=[task_research]
        )

        task_summarize = Task(
            description="Create a comprehensive markdown briefing with executive summary and insights.",
            expected_output="Polished markdown briefing (1000-1500 words).",
            agent=summarizer,
            context=[task_analyze]
        )

        news_crew = Crew(
            agents=[researcher, analyst, summarizer],
            tasks=[task_research, task_analyze, task_summarize],
            process=Process.sequential,
            verbose=True,
            memory=False,
            full_output=True
        )

        print("🤖 Running AI agent crew (this may take 2-5 minutes)...")
        result = news_crew.kickoff(inputs={'top_stories_count': TOP_STORIES_COUNT})

        print("✓ Crew execution completed")
        briefing = process_crew_result(result)

        if not briefing or len(briefing) < 200:
            print("⚠️ Insufficient output from AI -> using fallback")
            return generate_fallback_briefing()

        if '# ' not in briefing[:100]:
            briefing = f"# 🤖 Daily AI Intelligence Briefing\n\n{briefing}"

        briefing += f"\n\n---\n\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
        briefing += f"*Sources: {len(recent_articles_list)} articles | Profile: {FEED_PROFILE} | Model: {DEFAULT_MODEL}*\n"

        print(f"📝 Final briefing: {len(briefing)} characters")
        return briefing

    except Exception as e:
        print(f"❌ Crew execution error: {e}")
        import traceback
        traceback.print_exc()
        return generate_fallback_briefing()

if __name__ == '__main__':
    print("\n" + "="*80)
    print("=== AI NEWS AGENT - STANDALONE MODE ===")
    print("="*80)
    print(f"Model: {DEFAULT_MODEL} | Provider: {DEFAULT_PROVIDER}")
    print(f"API Key: {'✓ Configured' if GEMINI_KEY else '❌ Missing'}")
    print("="*80 + "\n")

    briefing = run_crew()

    print("\n" + "="*80)
    print("=== FINAL BRIEFING ===")
    print("="*80 + "\n")
    print(briefing)

    out_file = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    try:
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(briefing)
        print(f"\n✓ Saved to {out_file}")
    except Exception as e:
        print(f"\n❌ Save failed: {e}")