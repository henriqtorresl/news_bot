import re
from datetime import datetime, timedelta

import requests
from serpapi import GoogleSearch
from newspaper import Article
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
    Extrai o texto principal de uma notícia a partir da URL.
    Usa Newspaper3k e, se falhar, tenta Selenium como fallback. Loga erros em caso de falha.
    """
    article = Article(url)
    # 1. Tenta download usando o Newspaper3k
    try:
        article.download()
        article.parse()
        if article.text and len(article.text.strip()) > 0:
            return article.text
    except Exception as e:
        pass
    # 2. Fallback: Selenium sempre que o Newspaper3k falhar
    try:
        logger.info(f"Tentando Selenium para extrair conteúdo: {url}")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        html = driver.page_source
        article.set_html(html)
        driver.quit()
        article.parse()
        if article.text and len(article.text.strip()) > 0:
            return article.text
    except Exception as e3:
        logger.error(f"Error downloading content (Selenium fallback): {e3} | URL: {url}")
        return None
    logger.error(f"Error extracting text: Não foi possível extrair conteúdo de nenhuma forma | URL: {url}")
    return None


def fetch_google_news(term, api_key):
    """
    Busca notícias no Google News via SerpApi para um termo.
    Retorna lista de dicionários com dados das notícias.
    """
    params = {
        "engine": "google_news",
        "q": term + " when:1d", # último dia
        "hl": "pt-br",
        "gl": "br",
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
    Busca notícias no Bing News via SerpApi para um termo.
    Retorna lista de dicionários com dados das notícias.
    """
    params = {
        "engine": "bing_news",
        "q": term,
        "mkt": "pt-BR",
        "qft": "interval=\"7\"", # últimas 24 horas
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


def fetch_alerta_licitacao(term, api_key): # Validar se a lógica faz sentido
    """
    Busca licitações via API Alerta Licitação.
    Mapeia o retorno para o formato padrão do sistema.
    """
    url = "https://alertalicitacao.com.br/api/v1/licitacoesAbertas/"
    
    headers = {
        "Token": api_key
    }
    
    params = {
        "palavra_chave": term,
        "licitacoesPorPagina": 100
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"Erro API Alerta Licitação: {response.status_code} - {response.text}")
            return []

        data = response.json()
        licitacoes = data.get("licitacoes", [])
        
        results = []
        for lic in licitacoes:
            pub_date = None
            if lic.get("data_insercao"):
                try:
                    pub_date = datetime.strptime(lic.get("data_insercao"), "%Y-%m-%d")
                except:
                    pass

            results.append({
                'published_at': pub_date,
                'title': lic.get('titulo'),
                'source': f"Licitação - {lic.get('orgao')}",
                'url': lic.get('link'),
                'search_engine': 'alerta_licitacao',
                'raw_content': f"Modalidade: {lic.get('tipo')}. Objeto: {lic.get('objeto')}. Município: {lic.get('municipio')}-{lic.get('uf')}"
            })
            
        return results

    except Exception as e:
        logger.error(f"Error fetching Alerta Licitação: {e}")
        return []


def fetch_and_extract_news():
    """
    Busca notícias usando filtros, remove duplicadas, ordena por data e extrai conteúdo.
    Retorna lista final de notícias para análise/classificação.
    """
    try:
        google_api_key = env.GOOGLE_NEWS_API_KEY
        bing_api_key = env.BING_NEWS_API_KEY
        alerta_api_key = env.ALERTA_LICITACAO_API_KEY

        if not google_api_key or not bing_api_key or not alerta_api_key:
            raise ValueError("Google News API key and Bing News API key must be provided.")

        terms = get_filters()

        if not terms or len(terms) == 0:
            raise ValueError("No search terms found. Please configure filters in the database.")

        all_news = []
        for term in terms:
            google_news = fetch_google_news(term, google_api_key)
            bing_news = fetch_bing_news(term, bing_api_key)
            # licitacoes = fetch_alerta_licitacao(term, alerta_api_key)
            all_news.extend(google_news)
            all_news.extend(bing_news)
            # all_news.extend(licitacoes)
        # Deduplicação por URL
        seen_urls = set()
        unique_news = []
        for n in all_news:
            if n['url'] and n['url'] not in seen_urls:
                seen_urls.add(n['url'])
                unique_news.append(n)
        # Ordena por data (mais recente primeiro)
        sorted_news = sorted(unique_news, key=lambda x: x['published_at'] or datetime.min, reverse=True)
        # Extrai conteúdo de cada notícia
        for n in sorted_news:
            # Fazer uma validação aqui para não realizar o extract de notícias que eu ja tenho na minha base...
            n['raw_content'] = n['raw_content'] or extract_content(n['url'])
        return sorted_news
    except Exception as e:
        logger.error(f"Erro inesperado em fetch_and_extract_news: {e}")
        return []


def process_news():
    """
    Executa o pipeline de busca, extração e inserção de notícias na tabela raw_news.
    Loga o total de inseridas e duplicadas.
    """
    logger.info("Buscando notícias...")
    news_list = fetch_and_extract_news()
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