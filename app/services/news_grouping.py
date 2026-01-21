import json
import re

from openai import OpenAI

from app.config.environments import env
from app.config.logs import logger
from app.database.raw_news import get_relevant_news
from app.database.relevant_news import insert_relevant_news


client = OpenAI(api_key=env.OPENAI_API_KEY)


def group_news_by_theme(news_list):
    """
    Usa IA para agrupar notícias por tema/projeto.
    Retorna lista de grupos: [{'tema': ..., 'news_ids': [...], 'contextos': [...], 'titulos': [...], 'contents': [...]}]
    """
    
    # Prepara dados para o modelo
    prompt = (
        "Agrupe as notícias abaixo por tema/projeto. Cada grupo deve conter notícias que tratam do mesmo projeto, concessão ou evento, mesmo que usem palavras diferentes.\n"
        "Retorne SOMENTE em JSON, no formato: [{\"tema\": <nome do tema>, \"ids\": [id1, id2, ...]}].\n"
        "Notícias:\n"
    )
    for n in news_list:
        prompt += f"ID: {n['id']}\nTítulo: {n['title']}\nConteúdo: {n['raw_content'][:500]}\n---\n"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Você é especialista em infraestrutura pública."},
                      {"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.2,
        )
        result = response.choices[0].message.content.strip()
        match = re.search(r"\[.*\]", result, re.DOTALL)
        if match:
            result_json_str = match.group(0)
        else:
            result_json_str = result
        groups = json.loads(result_json_str)
        return groups
    except Exception as e:
        logger.error(f"Erro ao agrupar notícias por tema: {e}")
        return []

def process_and_save_relevant_news():
    """
    Busca notícias relevantes não agrupadas, agrupa, gera headline/resumo e salva na tabela relevant_news.
    Atualiza status das notícias para evitar retrabalho.
    """
    # Buscar notícias relevantes e não agrupadas
    news_list = get_relevant_news()
    if not news_list:
        logger.info("Nenhuma notícia relevante para agrupar.")
        return
    groups = group_news_by_theme(news_list)
    for group in groups:
        ids = group.get('ids', [])
        tema = group.get('tema', 'Tema não identificado')
        headlines = []
        summaries = []
        urls = []
        titles = []
        published_ats = []
        sources = []
        for nid in ids:
            n = next((x for x in news_list if x['id'] == nid), None)
            if n:
                headlines.append(n['title'])
                summaries.append(n['raw_content'][:500])
                urls.append(n['url'])
                titles.append(n['title'])
                published_ats.append(str(n.get('published_at', '')))
                sources.append(str(n.get('source', '')))
        prompt = (
            f"Gere um headline (máx 120 caracteres) e um resumo (máx 250 tokens) para o grupo de notícias sobre '{tema}'.\n"
            f"Responda no formato: HEADLINE | RESUMO\n"
            f"Notícias:\n" + '\n'.join(headlines) + '\n' + '\n'.join(summaries)
        )
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Você é especialista em infraestrutura pública."},
                          {"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.5,
            )
            result = response.choices[0].message.content.strip()
            regex = r"HEADLINE \| (.*)\s+RESUMO \| (.*)"
            match = re.search(regex, result, re.DOTALL)
            if match:
                headline = match.group(1).strip()
                ai_summary = match.group(2).strip()
        except Exception as e:
            headline = f"Erro IA: {e}"
            ai_summary = f"Erro IA: {e}"
        insert_relevant_news({
            'original_ids': ids,
            'original_urls': urls,
            'original_titles': titles,
            'published_ats': published_ats,
            'sources': sources,
            'tema': tema,
            'headline': headline,
            'ai_summary': ai_summary,
            'status': 'pending'
        })
        logger.info(f"Grupo '{tema}' salvo em relevant_news com {len(ids)} notícias.")
