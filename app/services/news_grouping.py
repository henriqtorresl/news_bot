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
    
    # Processa em lotes menores para evitar excesso de contexto
    BATCH_SIZE = 25
    all_groups = []
    for i in range(0, len(news_list), BATCH_SIZE):
        batch = news_list[i:i+BATCH_SIZE]
        prompt = (
            "Agrupe as notícias abaixo por tema/projeto. Cada grupo deve conter notícias que tratam do mesmo projeto, concessão ou evento, mesmo que usem palavras diferentes.\n"
            "Retorne SOMENTE em JSON, no formato: [{\"tema\": <nome do tema>, \"ids\": [id1, id2, ...]}].\n"
            "Notícias:\n"
        )
        for n in batch:
            # Reduz o conteúdo enviado para 200 caracteres
            prompt += f"ID: {n['id']}\nTítulo: {n['title']}\nConteúdo: {n['raw_content'][:200]}\n---\n"
        try:
            response = client.chat.completions.create(
                model="gpt-5.1",
                messages=[{"role": "system", "content": "Você é especialista em infraestrutura pública."},
                          {"role": "user", "content": prompt}],
                max_completion_tokens=2048,
                temperature=0.2,
            )
            result = response.choices[0].message.content.strip()
            logger.info(f"Resposta bruta da IA para agrupamento: {result}")
            match = re.search(r"\[.*\]", result, re.DOTALL)
            if match:
                result_json_str = match.group(0)
            else:
                result_json_str = result
            try:
                groups = json.loads(result_json_str)
                all_groups.extend(groups)
            except Exception as e:
                logger.error(f"Erro ao fazer json.loads da resposta da IA: {e}\nConteúdo recebido: {result_json_str}")
                continue
        except Exception as e:
            logger.error(f"Erro ao agrupar notícias por tema: {e}")
            continue
    return all_groups

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
        # Coleta dados individuais das notícias do grupo
        news_in_group = [n for n in news_list if n['id'] in ids]
        headlines = [n['title'] for n in news_in_group]
        summaries = [n['raw_content'][:500] for n in news_in_group]
        # Prompt para o grupo
        prompt = (
            f"Gere um headline (máx 120 caracteres) e um resumo (máx 250 tokens) para o grupo de notícias sobre '{tema}'.\n"
            "Responda EXATAMENTE neste formato, cada item em uma linha separada, sem texto extra:\n"
            "HEADLINE | <headline aqui>\n"
            "RESUMO | <resumo aqui>\n"
            "Não inclua explicações, apenas o texto no formato acima.\n"
            "Notícias:\n" + '\n'.join(headlines) + '\n' + '\n'.join(summaries)
        )
        headline = ""
        ai_summary = ""
        try:
            response = client.chat.completions.create(
                model="gpt-5.1",
                messages=[{"role": "system", "content": "Você é especialista em infraestrutura pública."},
                          {"role": "user", "content": prompt}],
                max_completion_tokens=300,
                temperature=0.5,
            )
            result = response.choices[0].message.content.strip()
            regex = r"HEADLINE \| (.*)\s+RESUMO \| (.*)"
            match = re.search(regex, result, re.DOTALL)
            if match:
                headline = match.group(1).strip()
                ai_summary = match.group(2).strip()
            else:
                headline = result[:120]
                ai_summary = result
        except Exception as e:
            headline = f"Erro IA: {e}"
            ai_summary = f"Erro IA: {e}"
        for n in news_in_group:
            insert_relevant_news({
                'original_ids': [n['id']],
                'original_urls': [n['url']],
                'original_titles': [n['title']],
                'published_at': str(n.get('published_at', '')) if n.get('published_at', '') else None,
                'sources': [str(n.get('source', ''))],
                'tema': tema,
                'headline': headline,
                'ai_summary': ai_summary,
                'status': 'pending'
            })
        logger.info(f"Grupo '{tema}' salvo em relevant_news com {len(news_in_group)} notícias.")
