import re
from datetime import datetime, timedelta

import requests
from serpapi import GoogleSearch
from newspaper import Article

from app.config.logs import logger
from app.config.environments import env
from app.database.filters import get_filters
from app.database.raw_news import insert_raw_news


def convert_relative_time(value, search_date):
    """
    Converte string de tempo relativo (ex: '2h', '3 dias') para datetime.
    """
    value = value.strip().lower()
    if "h" in value:
        hours = int(re.search(r"\d+", value).group())
        return search_date - timedelta(hours=hours)
    elif "m" in value:
        minutes = int(re.search(r"\d+", value).group())
        return search_date - timedelta(minutes=minutes)
    elif "dia" in value:
        days = int(re.search(r"\d+", value).group())
        return search_date - timedelta(days=days)
    else:
        return None


def extract_content(url):
    """
    Extrai o texto principal de uma notícia a partir da URL usando Newspaper3k.
    Tenta baixar e parsear o conteúdo, logando erros se ocorrerem.
    """
    article = Article(url)
    try:
        article.download()
    except Exception as e:
        try:
            response = requests.get(url, verify=False)
            article.set_html(response.text)
        except Exception as e2:
            logger.error(f"Error downloading content: {e2} | URL: {url}")
            return None
    try:
        article.parse()
        return article.text
    except Exception as e:
        logger.error(f"Error extracting text: {e} | URL: {url}")
        return None


def fetch_google_news(term, api_key):
    """
    Busca notícias no Google News via SerpApi para um termo específico.
    Retorna lista de dicionários com dados das notícias.
    """
    params = {
        "engine": "google_news",
        "q": term,
        "hl": "pt",
        "api_key": api_key
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        articles = results.get("news_results", [])
        news = []
        for art in articles:
            published_at = art.get('date', '')[:10]
            try:
                published_at = datetime.strptime(published_at, '%m/%d/%Y')
            except:
                published_at = None
            news.append({
                'published_at': published_at,
                'title': art.get('title'),
                'source': art.get('source', {}).get('name') if isinstance(art.get('source'), dict) else art.get('source'),
                'url': art.get('link'),
                'search_engine': 'google_news',
                'raw_content': None  
            })
        return news
    except Exception as e:
        logger.error(f"Error fetching Google News: {e}")
        return []


def fetch_bing_news(term, api_key):
    """
    Busca notícias no Bing News via SerpApi para um termo específico.
    Retorna lista de dicionários com dados das notícias.
    """
    params = {
        "engine": "bing_news",
        "q": term,
        "mkt": "pt-br",
        "qft": "sortbydate='1'",
        "api_key": api_key
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        articles = results.get("organic_results", [])
        search_date = datetime.now()
        news = []
        for art in articles:
            date_str = art.get('date', '')
            published_at = convert_relative_time(date_str, search_date) if date_str else None
            news.append({
                'published_at': published_at,
                'title': art.get('title'),
                'source': art.get('source'),
                'url': art.get('link'),
                'search_engine': 'bing_news',
                'raw_content': None  
            })
        return news
    except Exception as e:
        logger.error(f"Error fetching Bing News: {e}")
        return []


def fetch_and_extract_news(max_news):
    """
    Busca notícias usando filtros, remove duplicadas, ordena por data e extrai conteúdo.
    Retorna lista final de notícias para análise/classificação.
    """
    try:
        google_api_key = env.GOOGLE_NEWS_API_KEY
        bing_api_key = env.BING_NEWS_API_KEY

        if not google_api_key or not bing_api_key:
            raise ValueError("Google News API key and Bing News API key must be provided.")

        terms = get_filters()

        if not terms or len(terms) == 0:
            raise ValueError("No search terms found. Please configure filters in the database.")

        all_news = []
        for term in terms:
            google_news = fetch_google_news(term, google_api_key)
            bing_news = fetch_bing_news(term, bing_api_key)
            all_news.extend(google_news)
            all_news.extend(bing_news)
        # Deduplicação por URL
        seen_urls = set()
        unique_news = []
        for n in all_news:
            if n['url'] and n['url'] not in seen_urls:
                seen_urls.add(n['url'])
                unique_news.append(n)
        # Ordena por data (mais recente primeiro)
        sorted_news = sorted(unique_news, key=lambda x: x['published_at'] or datetime.min, reverse=True)
        sorted_news = sorted_news[:max_news]
        # Extrai conteúdo de cada notícia
        for n in sorted_news:
            n['raw_content'] = extract_content(n['url'])
        return sorted_news
    except Exception as e:
        logger.error(f"Erro inesperado em fetch_and_extract_news: {e}")
        return []


def process_news(max_news=50):
    """
    Orquestra o pipeline de busca, extração e inserção de notícias na base raw_news.
    Loga quantidade de inseridas e duplicadas.
    """
    logger.info("Buscando notícias...")
    news_list = fetch_and_extract_news(max_news=max_news)
    logger.info(f"Total de notícias encontradas: {len(news_list)}")

    inserted = 0
    duplicated = 0
    for i, news in enumerate(news_list, 1):
        result = insert_raw_news(news)
        if result:
            inserted += 1
        else:
            duplicated += 1
        logger.info(f"{i}. {news['title']} | Fonte: {news['source']} | URL: {news['url']}")
        logger.info(f"Conteúdo (primeiros 100 chars): {news['raw_content'][:100] if news['raw_content'] else 'N/A'}\n")

    logger.info(f"Notícias inseridas: {inserted}")
    logger.info(f"Ignoradas por duplicidade/erro: {duplicated}")