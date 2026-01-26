import json
import re

from openai import OpenAI

from app.config.environments import env
from app.config.logs import logger
from app.database.raw_news import get_unclassified_news, update_news_relevance


client = OpenAI(api_key=env.OPENAI_API_KEY)


def classify_news_relevance(news_list, user_examples=None):
    """
    Classifica relevância e contexto das notícias usando IA (OpenAI/GPT).
    Recebe lista de notícias e exemplos do usuário (opcional).
    Retorna lista de dicts com id, nota e contexto.
    """
    results = []
    for news in news_list:
        # Monta prompt para classificação
        prompt = (
            "Você é um especialista em infraestrutura pública. Avalie a relevância da notícia abaixo para o contexto de concessões e PPPs no Brasil.\n"
            "Dê uma nota de 0 a 10 (onde 0 = irrelevante, 10 = extremamente relevante) e explique o contexto em 1 frase.\n"
            "Responda SOMENTE no formato JSON, sem explicações extras. Exemplo: {\"nota\": 8, \"contexto\": \"Notícia relevante sobre concessão ferroviária.\"}\n"
        )
        if user_examples:
            prompt += "\nExemplos de notícias que o usuário considera relevantes/irrelevantes:\n"
            for ex in user_examples:
                prompt += f"Título: {ex['title']}\nRelevância: {ex['relevance']}\n"
        prompt += f"\nNotícia:\n{news['raw_content']}\n"
        try:
            response = client.chat.completions.create(
                model="gpt-5.1",
                messages=[
                    {"role": "system", "content": "Você é especialista em infraestrutura pública."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=256,
                temperature=0.2,
            )
            result = response.choices[0].message.content.strip()
            if not result:
                logger.error(f"Resposta vazia do modelo para notícia id={news['id']}")
                results.append({'id': news['id'], 'relevance': None, 'context': 'Erro: resposta vazia do modelo'})
                continue
            # Extrai JSON da resposta do modelo
            match = re.search(r"{.*}", result, re.DOTALL)
            if match:
                result_json_str = match.group(0)
            else:
                result_json_str = result
            try:
                result_json = json.loads(result_json_str)
                results.append({
                    'id': news['id'],
                    'relevance': result_json.get('nota'),
                    'context': result_json.get('contexto')
                })
            except Exception as e:
                logger.error(f"Resposta bruta do modelo para notícia id={news['id']}: {result}")
                results.append({'id': news['id'], 'relevance': None, 'context': f'Erro ao decodificar JSON: {e}'})
        except Exception as e:
            logger.error(f"Erro na requisição OpenAI para notícia id={news['id']}: {e}")
            results.append({'id': news['id'], 'relevance': None, 'context': f'Erro: {e}'})
    return results


def filter_out_portugal_news(list):
    # Filtra notícias de Portugal (domínio .pt)
    filtered_list = []
    for news in list:
        url = news.get('url', '')
        if not url:
            filtered_list.append(news)
            continue
        # Remove se domínio termina com .pt ou contém .pt/
        if re.search(r'\.pt([/\:]|$)', url):
            logger.info(f"Notícia ignorada por domínio .pt: {url}")
            continue
        filtered_list.append(news)
    
    return filtered_list


def classify_and_update_all(user_examples=None):
    """
    Busca notícias não classificadas, classifica com IA e atualiza no banco.
    Loga quantidade processada.
    """
    news_list = get_unclassified_news()
    if not news_list:
        logger.info("Nenhuma notícia nova para classificar.")
        return

    filtered_news_list = filter_out_portugal_news(news_list)

    results = classify_news_relevance(filtered_news_list, user_examples)
    for r in results:
        update_news_relevance(r['id'], r['relevance'], r['context'])
    logger.info(f"{len(results)} notícias classificadas e atualizadas.")
