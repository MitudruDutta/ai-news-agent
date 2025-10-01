# file: agent_crew.py
"""Crew setup to research, analyze, and summarize recent AI news articles.

Workflow:
1. Fetch recent articles via diversified RSS feeds (industry + academic + MIT research).
2. Researcher fetches full text (using extraction tool) for a balanced subset.
3. Analyst selects top 3 impactful stories ensuring diversity (at least 1 academic/research if available).
4. Summarizer produces concise executive summaries.

Environment overrides:
- FEED_PROFILE = extended|base (default extended) controls breadth of feeds.
- EXTRA_FEEDS = comma separated additional RSS URLs.
- FEED_MAX_ARTICLES (int) cap after balancing (default 40 for extended, 20 for base).
- FEED_MAX_PER_DOMAIN (int) per-domain cap (default 3).
- FEED_LOOKBACK_HOURS (int) window (default 24).
"""
from __future__ import annotations

from typing import List, Dict, Any
from dotenv import load_dotenv
import os

# --- Model / Provider selection ---------------------------------------------
# Priority: GEMINI_API_KEY -> OPENAI_API_KEY -> default placeholder
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Normalize model names to what litellm / providers expect.
if GEMINI_KEY:
    default_gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    DEFAULT_MODEL = f"gemini/{default_gemini_model}" if "/" not in default_gemini_model else default_gemini_model
elif OPENAI_KEY:
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    DEFAULT_MODEL = f"openai/{openai_model}" if "/" not in openai_model else openai_model
else:
    DEFAULT_MODEL = os.getenv("AGENT_MODEL", "openai/gpt-4o-mini")

# --- Optional dependency guards ---
CREW_AVAILABLE = True
try:
    from crewai import Agent, Task, Crew, Process  # type: ignore
    try:  # newer versions may expose a 'tool' utility elsewhere
        from crewai.tools import tool  # type: ignore
    except Exception:  # pragma: no cover
        def tool(name: str):  # type: ignore
            def _wrap(fn):
                return fn
            return _wrap
except ImportError:  # pragma: no cover
    CREW_AVAILABLE = False
    # Provide light-weight stand-ins to avoid NameErrors if referenced accidentally.
    class _Stub:  # minimal placeholder
        def __init__(self, *a, **k):
            pass
    Agent = Task = Crew = Process = _Stub  # type: ignore
    def tool(name: str):  # type: ignore
        def _wrap(fn):
            return fn
        return _wrap

try:  # Optional tools package
    from crewai_tools import ScrapeWebsiteTool  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    ScrapeWebsiteTool = None  # type: ignore

# --- OPTIONAL: dynamic source configuration ---------------------------------
try:
    from sources_config import PROFILE_MAP  # type: ignore
except Exception:
    PROFILE_MAP = {}

from news_fetcher import fetch_recent_articles, extract_article_text  # updated import remains

# Forward declarations to satisfy type checkers when CREW_AVAILABLE is False
researcher = None  # type: ignore
analyst = None  # type: ignore
summarizer = None  # type: ignore

# Feed profile resolution
_feed_profile = os.getenv("FEED_PROFILE", "extended").lower()
base_feeds = PROFILE_MAP.get(_feed_profile, PROFILE_MAP.get("extended", [])) or [
    'https://openai.com/blog/rss.xml',
    'https://deepmind.google/blog/rss.xml',
    'https://www.kdnuggets.com/feed',
    'https://techcrunch.com/category/artificial-intelligence/feed/',
    'https://news.mit.edu/topic/artificial-intelligence2-rss',
]

_extra_raw = os.getenv("EXTRA_FEEDS", "").strip()
if _extra_raw:
    extra_list = [u.strip() for u in _extra_raw.split(',') if u.strip()]
else:
    extra_list = []

ai_news_feeds: List[str] = list(dict.fromkeys(base_feeds + extra_list))  # preserve order, de-dup

# Balancing / limits
_default_cap = 40 if _feed_profile == 'extended' else 20
_max_articles = int(os.getenv("FEED_MAX_ARTICLES", str(_default_cap)))
_max_per_domain = int(os.getenv("FEED_MAX_PER_DOMAIN", "3"))
_lookback_hours = int(os.getenv("FEED_LOOKBACK_HOURS", "24"))

recent_articles_list: List[Dict[str, Any]] = fetch_recent_articles(
    ai_news_feeds,
    max_articles=_max_articles,
    max_per_domain=_max_per_domain,
    hours=_lookback_hours,
)

# Academic injection fallback: ensure at least one academic/research domain if possible
ACADEMIC_DOMAINS = {"news.mit.edu", "export.arxiv.org", "arxiv.org", "bair.berkeley.edu"}
if recent_articles_list:
    have_academic = any(any(dom in (a.get('link') or '') for dom in ACADEMIC_DOMAINS) for a in recent_articles_list)
    if not have_academic:
        academic_feeds = [f for f in ai_news_feeds if any(k in f for k in ["arxiv", "mit.edu", "bair.berkeley.edu"])]
        if academic_feeds:
            academic_articles = fetch_recent_articles(
                academic_feeds,
                max_articles=5,
                max_per_domain=2,
                hours=_lookback_hours,
            )
            existing_links = {a.get('link') for a in recent_articles_list}
            for ac in academic_articles:
                if ac.get('link') not in existing_links:
                    recent_articles_list.insert(0, ac)
                    break

# --- Helper Tool Wrapper(s) --------------------------------------------------
@tool("Article Text Fetcher")
def article_text_tool(url: str) -> str:
    """Return cleaned article text for a URL.
    Use this tool when you need the full body content of an article whose link you have.
    """
    return extract_article_text(url)

# Only build agents & tasks if crewai actually available
if CREW_AVAILABLE:
    researcher = Agent(
        role='AI News Researcher',
        goal='Find and extract the full text of recent, relevant AI news articles.',
        backstory=(
            "You are a diligent and expert researcher specializing in Artificial Intelligence. "
            "Your mission is to scan the web for the latest breakthroughs and announcements in the AI field. "
            "You are known for your ability to quickly find and retrieve the complete text of articles from any given URL."
        ),
        verbose=True,
        allow_delegation=False,
        llm=DEFAULT_MODEL,
    )

    analyst = Agent(
        role='Principal AI News Analyst',
        goal='Analyze a collection of AI news articles and identify the top 3 most significant stories of the day.',
        backstory=(
            "You are a seasoned AI analyst with a deep understanding of the industry. "
            "You have a keen eye for what truly matters, and you can distinguish between marketing fluff and genuine technological advancements. "
            "Your goal is to read through a list of articles and select only the most impactful and newsworthy stories to brief your executive team."
        ),
        verbose=True,
        allow_delegation=False,
        llm=DEFAULT_MODEL,
    )

    summarizer = Agent(
        role='Expert AI News Summarizer',
        goal='Create concise, clear summaries for each of the selected top AI news articles.',
        backstory=(
            "You are a skilled writer and editor with a talent for distillation. "
            "You transform complex technical articles into clear, compelling summaries ideal for an executive briefing."
        ),
        verbose=True,
        allow_delegation=False,
        llm=DEFAULT_MODEL,
    )

    for _agent in (researcher, analyst, summarizer):  # Attempt to apply model attr if supported
        try:
            setattr(_agent, 'model', DEFAULT_MODEL)
        except Exception:
            pass

# Optional fallback if feeds empty and user allows placeholders
if not recent_articles_list and os.getenv("ALLOW_PLACEHOLDER_ARTICLES", "true").lower() in {"1", "true", "yes", "y"}:
    recent_articles_list = [
        {
            "title": "OpenAI Announces GPT-5 with Enhanced Reasoning Capabilities",
            "link": "https://openai.com/blog/gpt-5-announcement",
            "published": "2025-10-02 08:00:00 UTC",
            "text": "OpenAI today unveiled GPT-5, featuring significant improvements in mathematical reasoning, code generation, and multimodal understanding. The new model demonstrates 40% better performance on complex reasoning tasks compared to GPT-4, with enhanced safety measures and reduced hallucination rates. The model will be available through API access starting next month, with enterprise customers getting priority access."
        },
        {
            "title": "Google DeepMind's AlphaCode 3 Achieves Human-Level Programming Performance",
            "link": "https://deepmind.google/blog/alphacode-3-breakthrough",
            "published": "2025-10-02 06:30:00 UTC",
            "text": "DeepMind's latest AlphaCode 3 system has achieved human-level performance on competitive programming challenges, solving 85% of problems that typically stump professional developers. The system combines advanced reasoning with real-time code execution feedback, marking a significant milestone in AI-assisted software development. The technology is being integrated into Google's developer tools and will be available to select partners in Q1 2025."
        },
        {
            "title": "Meta Releases Llama 3.1 with 405B Parameters and Open Source License",
            "link": "https://ai.meta.com/blog/llama-3-1-release",
            "published": "2025-10-01 14:00:00 UTC",
            "text": "Meta has released Llama 3.1, its largest open-source language model with 405 billion parameters, rivaling GPT-4 in performance while maintaining full open-source availability. The model excels in multilingual tasks, code generation, and reasoning, with optimizations for efficient inference on consumer hardware. This release represents Meta's commitment to democratizing advanced AI capabilities and fostering innovation in the open-source community."
        }
    ]

# Build a readable (short) context: cap to first 8 diverse domains
_seen_domains = set()
context_articles = []
for art in recent_articles_list:
    link = art.get('link', '')
    dom = link.split('/')[2] if '://' in link else link
    if dom not in _seen_domains:
        _seen_domains.add(dom)
        context_articles.append(art)
    if len(context_articles) >= 8:
        break
articles_context_str = "\n".join(
    f"Title: {a.get('title','N/A')}\nLink: {a.get('link','')}" for a in context_articles
)

# Enhanced task instructions (only if crew available)
if CREW_AVAILABLE:
    researcher_prompt_extra = (
        "IMPORTANT: Ensure you attempt extraction for ALL provided URLs (not just the first few). "
        "If extraction fails (e.g., 403), include the metadata with an empty 'text' field. "
        "Preserve ordering but do not duplicate entries."
    )
    analysis_prompt_extra = (
        "DIVERSITY RULES: Prefer a mix that includes (1) at least one academic / research source (e.g., arXiv, MIT, BAIR, university lab) if present, "
        "(2) one industry / corporate development (e.g., OpenAI, Google, Meta, NVIDIA), and (3) one broader ecosystem / tooling / standards or open-source item. "
        "If academic sources are absent in the input, state that constraint explicitly in rationale. "
        "When ranking impact, weigh: novelty of technique, quantitative performance deltas, openness (open-source / reproducibility), and downstream economic or safety implications."
    )
    summary_prompt_extra = (
        "For each summary: Sentence 1 = factual headline outcome; Sentence 2 = why it matters (impact, metrics); Optional Sentence 3 = forward-looking implication or open question. "
        "If any article lacked extracted text, rely on title + source but explicitly mark '(text unavailable)'."
    )

    task_research = Task(
        description=(
            "For each article below, retrieve the full text. Use the tool 'Article Text Fetcher' with each URL. "
            "Return a JSON array where each element has: title, link, published, text.\n\nARTICLES:\n{context}\n\n" + researcher_prompt_extra
        ),
        expected_output=(
            "A JSON array of article objects: [{ 'title': str, 'link': str, 'published': str, 'text': str }]. Ensure valid JSON."
        ),
        agent=researcher,
        tools=[article_text_tool],
    )

    task_analyze = Task(
        description=(
            "You are given the full article objects from the researcher. Analyze them to select the top 3 most impactful AI news stories today. "
            "Impact factors: novelty, industry significance, technical depth, potential business/research implications. "
            + analysis_prompt_extra + " Provide a JSON object with keys: 'selected' (array of 3 article objects), 'rationale' (array of explanations), 'criteria_summary'."
        ),
        expected_output=(
            "A JSON object: { 'selected': [3 article objects], 'rationale': [3 strings], 'criteria_summary': str }."
        ),
        agent=analyst,
        context=[task_research],
    )

    task_summarize = Task(
        description=(
            "You receive the analysis object. For each selected article, craft a concise 2-3 sentence executive summary focusing on the 'what', 'why it matters', metrics, and implications. "
            + summary_prompt_extra + " Return a final structured markdown report with a heading 'Daily AI Briefing', then numbered sections for each article with title, summary, and original link."
        ),
        expected_output=("A markdown report ready for executive consumption."),
        agent=summarizer,
        context=[task_analyze],
    )

    news_crew = Crew(
        agents=[researcher, analyst, summarizer],
        tasks=[task_research, task_analyze, task_summarize],
        process=Process.sequential,
        verbose=True,
    )

# --- Offline Fallback (no API keys or crew library) -------------------------

def _offline_fallback_summary() -> str:
    lines = ["# Daily AI Briefing (Offline Fallback)", "", "LLM pipeline unavailable; showing raw placeholder summaries."]
    for idx, art in enumerate(recent_articles_list[:3], start=1):
        lines.append(f"## {idx}. {art['title']}")
        lines.append(f"Source: {art['link'] or 'N/A'}")
        lines.append("Summary: (Fallback) This is a placeholder summary because model API key or crew backend is not available.")
        lines.append("")
    return "\n".join(lines)

# --- Result Coercion Helper -------------------------------------------------

def _coerce_briefing(result: Any) -> str:
    """Coerce various crewai kickoff return types into a briefing string.

    Handles:
      - Direct string
      - Dict with common keys (final_output, output, result, response, content)
      - Object with attributes (final_output, output, raw, response)
      - List -> joined strings if all elements stringy
    Falls back to repr(result) if nothing meaningful extracted.
    """
    if result is None:
        return ""  # caller will handle empty
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("final_output", "output", "result", "response", "content"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val
        # No direct string — attempt to stringify selected portion
        try:
            import json  # local import
            return json.dumps(result, ensure_ascii=False, indent=2)[:8000]
        except Exception:
            return repr(result)
    if isinstance(result, list):
        # If list of strings or dicts with 'summary'
        collected: list[str] = []
        for item in result:
            if isinstance(item, str):
                collected.append(item)
            elif isinstance(item, dict):
                summary = item.get('summary') or item.get('text') or ''
                if isinstance(summary, str) and summary.strip():
                    collected.append(summary.strip())
        if collected:
            return "\n\n".join(collected)
    # Attribute-based objects
    for attr in ("final_output", "output", "raw", "response", "content"):
        if hasattr(result, attr):
            val = getattr(result, attr)
            if isinstance(val, str) and val.strip():
                return val
    # Fallback generic repr
    return repr(result)[:8000]

# --- Runner ------------------------------------------------------------------

def run_crew() -> Any:
    """Run the crew pipeline and return the final summarized report (guaranteed string or diagnostic)."""
    if not recent_articles_list:
        return "No recent or placeholder articles available to process."

    # If no provider keys OR crew library missing, use offline fallback.
    if not (GEMINI_KEY or OPENAI_KEY) or not CREW_AVAILABLE:
        return _offline_fallback_summary()

    # Execute crew with defensive capture
    try:  # pragma: no cover - integration path
        raw_result = news_crew.kickoff(inputs={'context': articles_context_str})  # type: ignore
    except Exception as e:  # If crew itself fails, degrade gracefully
        return ("# Daily AI Briefing (Degraded)\n\n"
                "Crew execution failed; providing fallback context.\n\n"
                f"Error: {e}\n\n"
                + _offline_fallback_summary())

    briefing = _coerce_briefing(raw_result)
    # Post-process: ensure we have at least some recognizable headings
    if not briefing or not briefing.strip():
        diagnostic = ("# Daily AI Briefing (Empty Output)\n\nThe crew pipeline completed but produced an empty or unrecognized result. "
                      "Fallback summary inserted below.\n\n")
        briefing = diagnostic + _offline_fallback_summary()
    elif 'Daily AI Briefing' not in briefing:
        # Normalize formatting to expected heading for downstream consumers (email subject detection etc.)
        briefing = "# Daily AI Briefing\n\n" + briefing.strip()

    return briefing

if __name__ == '__main__':  # Manual execution
    print(f"Model in use: {DEFAULT_MODEL}")
    print(f"Gemini Key? {bool(GEMINI_KEY)} | OpenAI Key? {bool(OPENAI_KEY)} | Crew Available? {CREW_AVAILABLE}")
    print(f"Feeds configured: {len(ai_news_feeds)} | Articles found (or placeholders): {len(recent_articles_list)}")
    if not recent_articles_list:
        print("No new articles to process. Exiting.")
    else:
        offline = (not (GEMINI_KEY or OPENAI_KEY) or not CREW_AVAILABLE)
        print(f"Starting pipeline (offline fallback={'yes' if offline else 'no'}) with {len(recent_articles_list)} articles...")
        final_briefing = run_crew()
        print("\n[Debug] Briefing length:", len(final_briefing) if isinstance(final_briefing, str) else 'n/a')
        print("\n--- FINAL BRIEFING ---\n")
        print(final_briefing)
