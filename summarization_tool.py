# file: summarization_tool.py
"""
Advanced Summarization Tools for AI News Articles
Supports multiple summarization strategies and quality assessment
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIGURATION (Gemini-only) ====================

# Summarization settings
SUMMARY_LENGTH = os.getenv('SUMMARY_LENGTH', 'medium')  # short, medium, long
MAX_SUMMARY_SENTENCES = {
    'short': 2,
    'medium': 3,
    'long': 5
}

# AI Model configuration
USE_AI_SUMMARIZATION = os.getenv('USE_AI_SUMMARIZATION', 'true').lower() == 'true'
GEMINI_KEY = os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')

# Quality thresholds
MIN_SUMMARY_LENGTH = int(os.getenv('MIN_SUMMARY_LENGTH', '50'))
MIN_RELEVANCE_SCORE = float(os.getenv('MIN_RELEVANCE_SCORE', '0.6'))

# ==================== AI MODEL INITIALIZATION (Gemini only) ====================

llm_available = False
llm_instance = None

if USE_AI_SUMMARIZATION and GEMINI_KEY:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm_instance = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=GEMINI_KEY
        )
        llm_available = True
        print("✓ Using Gemini for AI summarization")
    except Exception as e:
        print(f"⚠️ Gemini initialization failed: {e}. Falling back to extractive summarization only.")
        llm_available = False
elif USE_AI_SUMMARIZATION and not GEMINI_KEY:
    print("⚠️ No GEMINI_API_KEY provided. Falling back to extractive summarization only.")
else:
    print(f"🔧 AI Summarization: {'Disabled' if not USE_AI_SUMMARIZATION else 'No API Key'}")

print(f"🔑 GEMINI_KEY Status: {'✓ Found' if GEMINI_KEY else '❌ Missing'}")

# ==================== TEXT PREPROCESSING ====================

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters
    text = re.sub(r'[^\w\s.,!?;:()\-\'\"]+', '', text)

    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)

    return text.strip()


def extract_sentences(text: str) -> List[str]:
    """Extract sentences from text"""
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+', text)

    # Clean and filter
    sentences = [s.strip() for s in sentences if s.strip()]
    sentences = [s for s in sentences if len(s) > 20]  # Minimum length

    return sentences


def calculate_sentence_importance(sentence: str, keywords: List[str]) -> float:
    """
    Calculate importance score for a sentence based on keywords

    Args:
        sentence: The sentence to score
        keywords: List of important keywords

    Returns:
        Importance score (0.0 to 1.0)
    """
    sentence_lower = sentence.lower()

    # Count keyword occurrences
    keyword_count = sum(1 for kw in keywords if kw.lower() in sentence_lower)

    # Calculate score
    score = min(keyword_count / len(keywords), 1.0) if keywords else 0.5

    # Bonus for first sentences
    return score


# ==================== EXTRACTIVE SUMMARIZATION ====================

def extractive_summarization(
        text: str,
        max_sentences: int = 3,
        keywords: Optional[List[str]] = None
) -> str:
    """
    Create summary by extracting most important sentences

    Args:
        text: Full text to summarize
        max_sentences: Maximum number of sentences in summary
        keywords: Optional list of keywords to prioritize

    Returns:
        Extractive summary
    """
    if not text:
        return ""

    # Clean text
    text = clean_text(text)

    # Extract sentences
    sentences = extract_sentences(text)

    if len(sentences) <= max_sentences:
        return '. '.join(sentences) + '.'

    # Default keywords if none provided
    if not keywords:
        keywords = ['AI', 'machine learning', 'model', 'algorithm', 'research',
                    'performance', 'breakthrough', 'innovation', 'development']

    # Score sentences
    scored_sentences = [
        (sentence, calculate_sentence_importance(sentence, keywords))
        for sentence in sentences
    ]

    # Sort by score and take top sentences
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    top_sentences = [s[0] for s in scored_sentences[:max_sentences]]

    # Reorder to maintain original sequence
    top_sentences.sort(key=lambda s: sentences.index(s))

    return '. '.join(top_sentences) + '.'


# ==================== AI-POWERED SUMMARIZATION ====================

def ai_summarization(text: str, max_words: int = 100) -> Optional[str]:
    """
    Create summary using AI language model

    Args:
        text: Full text to summarize
        max_words: Maximum words in summary

    Returns:
        AI-generated summary or None if failed
    """
    if not llm_available or not llm_instance:
        return None

    try:
        prompt = f"""Summarize the following AI/ML news article in {max_words} words or less. 
Focus on:
1. Main finding or announcement
2. Key technical details or metrics
3. Significance and impact

Article text:
{text[:3000]}

Concise summary:"""

        response = llm_instance.invoke(prompt)

        # Extract text from response
        if hasattr(response, 'content'):
            summary = response.content
        else:
            summary = str(response)

        return clean_text(summary)

    except Exception as e:
        print(f"⚠️ AI summarization failed: {e}")
        return None


# ==================== HYBRID SUMMARIZATION ====================

def hybrid_summarization(
        text: str,
        strategy: str = 'auto'
) -> str:
    """
    Create summary using hybrid approach (AI + extractive)

    Args:
        text: Full text to summarize
        strategy: Summarization strategy ('ai', 'extractive', 'auto')

    Returns:
        Summary text
    """
    if not text:
        return "No content available for summarization."

    # Determine max sentences based on length setting
    max_sentences = MAX_SUMMARY_SENTENCES.get(SUMMARY_LENGTH, 3)

    # Auto strategy: try AI first, fallback to extractive
    if strategy == 'auto':
        if llm_available:
            ai_summary = ai_summarization(text, max_words=max_sentences * 30)
            if ai_summary and len(ai_summary) >= MIN_SUMMARY_LENGTH:
                return ai_summary

        # Fallback to extractive
        return extractive_summarization(text, max_sentences=max_sentences)

    # AI strategy
    elif strategy == 'ai':
        summary = ai_summarization(text, max_words=max_sentences * 30)
        return summary if summary else extractive_summarization(text, max_sentences=max_sentences)

    # Extractive strategy
    else:
        return extractive_summarization(text, max_sentences=max_sentences)


# ==================== ARTICLE SUMMARIZATION ====================

def summarize_article(article: Dict[str, Any], strategy: str = 'auto') -> Dict[str, Any]:
    """
    Summarize a single article

    Args:
        article: Article dictionary with 'title', 'text', 'summary' fields
        strategy: Summarization strategy

    Returns:
        Article dictionary with added 'generated_summary' field
    """
    # Extract text to summarize
    text = article.get('text') or article.get('summary') or article.get('title', '')

    if not text or len(text) < MIN_SUMMARY_LENGTH:
        article['generated_summary'] = article.get('summary', 'No summary available.')
        article['summary_method'] = 'original'
        return article

    # Generate summary
    summary = hybrid_summarization(text, strategy=strategy)

    # Add to article
    article['generated_summary'] = summary
    article['summary_method'] = 'ai' if (llm_available and strategy != 'extractive') else 'extractive'
    article['summary_timestamp'] = datetime.now().isoformat()

    return article


def summarize_articles(
        articles: List[Dict[str, Any]],
        strategy: str = 'auto',
        parallel: bool = False
) -> List[Dict[str, Any]]:
    """
    Summarize multiple articles

    Args:
        articles: List of article dictionaries
        strategy: Summarization strategy
        parallel: Whether to process in parallel (requires concurrent.futures)

    Returns:
        List of articles with summaries
    """
    if not articles:
        return []

    print(f"\n📝 Summarizing {len(articles)} articles using '{strategy}' strategy...")

    if parallel:
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(summarize_article, article, strategy): i
                    for i, article in enumerate(articles)
                }

                results = [None] * len(articles)
                for future in as_completed(futures):
                    idx = futures[future]
                    results[idx] = future.result()

                print(f"✓ Completed parallel summarization")
                return results

        except Exception as e:
            print(f"⚠️ Parallel processing failed: {e}. Using sequential processing.")

    # Sequential processing
    summarized = []
    for i, article in enumerate(articles, 1):
        print(f"  Processing {i}/{len(articles)}...", end='\r')
        summarized.append(summarize_article(article, strategy=strategy))

    print(f"✓ Completed summarization of {len(summarized)} articles")
    return summarized


# ==================== QUALITY ASSESSMENT ====================

def assess_summary_quality(summary: str, original_text: str) -> Dict[str, Any]:
    """
    Assess the quality of a summary

    Args:
        summary: Generated summary
        original_text: Original text

    Returns:
        Quality metrics dictionary
    """
    metrics = {
        'length': len(summary),
        'compression_ratio': len(summary) / len(original_text) if original_text else 0,
        'sentence_count': len(extract_sentences(summary)),
        'quality_score': 0.0
    }

    # Calculate quality score
    score = 0.0

    # Length check
    if MIN_SUMMARY_LENGTH <= metrics['length'] <= 500:
        score += 0.3

    # Compression check (good summaries are 10-30% of original)
    if 0.1 <= metrics['compression_ratio'] <= 0.3:
        score += 0.3

    # Sentence count check
    if 2 <= metrics['sentence_count'] <= 5:
        score += 0.2

    # Keyword presence
    ai_keywords = ['ai', 'model', 'algorithm', 'research', 'learning', 'data']
    keyword_count = sum(1 for kw in ai_keywords if kw in summary.lower())
    score += min(keyword_count / len(ai_keywords), 0.2)

    metrics['quality_score'] = score
    metrics['quality_rating'] = (
        'excellent' if score >= 0.8 else
        'good' if score >= 0.6 else
        'fair' if score >= 0.4 else
        'poor'
    )

    return metrics


# ==================== STANDALONE EXECUTION ====================

if __name__ == '__main__':
    # Test summarization
    test_article = {
        'title': 'Breakthrough in Large Language Models',
        'text': """
        Researchers at a leading AI lab have announced a significant breakthrough in large language model architecture. 
        The new model, called TransformerX, achieves state-of-the-art performance across multiple benchmarks while using 
        40% fewer parameters than existing models. This efficiency gain is attributed to a novel attention mechanism 
        that better captures long-range dependencies in text. The model demonstrated 95% accuracy on complex reasoning 
        tasks, surpassing previous models by a significant margin. The research team plans to open-source the model 
        architecture in the coming months, which could democratize access to advanced AI capabilities. Industry experts 
        believe this development could accelerate AI adoption across various sectors, from healthcare to finance. 
        The breakthrough also addresses concerns about the environmental impact of training large models, as the 
        reduced parameter count translates to lower computational requirements and energy consumption.
        """
    }

    print("=" * 80)
    print("SUMMARIZATION TOOL - TEST")
    print("=" * 80)

    # Test extractive summarization
    print("\n1. Extractive Summarization:")
    extractive_summary = extractive_summarization(test_article['text'], max_sentences=3)
    print(extractive_summary)

    # Test AI summarization
    if llm_available:
        print("\n2. AI Summarization:")
        ai_summary = ai_summarization(test_article['text'], max_words=100)
        if ai_summary:
            print(ai_summary)
        else:
            print("AI summarization not available")

    # Test hybrid summarization
    print("\n3. Hybrid Summarization:")
    hybrid_summary = hybrid_summarization(test_article['text'], strategy='auto')
    print(hybrid_summary)

    # Test quality assessment
    print("\n4. Quality Assessment:")
    quality = assess_summary_quality(hybrid_summary, test_article['text'])
    print(f"Quality Score: {quality['quality_score']:.2f} ({quality['quality_rating']})")
    print(f"Length: {quality['length']} characters")
    print(f"Compression Ratio: {quality['compression_ratio']:.2%}")
    print(f"Sentence Count: {quality['sentence_count']}")

    print("\n" + "=" * 80)