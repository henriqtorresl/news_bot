from datetime import datetime

from sqlalchemy import text

from app.config.database import Session
from app.config.logs import logger


def insert_relevant_news(news_group):
    db = Session()
    query = text("""
        INSERT INTO relevant_news (original_url, original_title, published_at, source, topic, headline, ai_summary, status)
        VALUES (:original_url, :original_title, :published_at, :source, :topic, :headline, :ai_summary, :status)
        ON CONFLICT (original_url) DO NOTHING
    """)
    try:
        original_urls = news_group.get('original_urls', [])
        original_titles = news_group.get('original_titles', [])
        sources = news_group.get('sources', [])
        published_at = news_group.get('published_at')
        if not original_urls:
            logger.error("original_urls não fornecido para o grupo relevante!")
            db.close()
            return
        result = db.execute(query, {
            "original_url": original_urls[0] if original_urls else None,
            "original_title": original_titles[0] if original_titles else None,
            "published_at": published_at if published_at else None,
            "source": sources[0] if sources else None,
            "topic": news_group.get('tema'),
            "headline": news_group.get('headline'),
            "ai_summary": news_group.get('ai_summary'),
            "status": news_group.get('status', 'pending')
        })
        db.commit()
        if result.rowcount > 0:
            logger.info(f"Notícia relevante inserida: {news_group.get('tema')} - {original_urls[0] if original_urls else ''}")
        else:
            logger.info(f"Notícia relevante já existia, não inserida: {news_group.get('tema')} - {original_urls[0] if original_urls else ''}")
    except Exception as e:
        logger.error(f"Erro ao inserir grupo relevante: {e}")
        db.rollback()
    finally:
        db.close()


def get_news_to_sent():
	db = Session()
	query = text("""
        SELECT * FROM relevant_news
        WHERE status = 'pending' OR status = 'error'
        ORDER BY published_at DESC
	""")
	try:
		result = db.execute(query)
		news = [dict(row._mapping) for row in result]
		logger.info(f"{len(news)} notícias para envio encontradas.")
		return news
	except Exception as e:
		logger.error(f"Erro ao buscar notícias para envio: {e}")
		return []
	finally:
		db.close()


def update_news_status_and_sent_at(news_ids, status):
    db = Session()
    now = datetime.now()
    if not news_ids or not isinstance(news_ids, list):
        logger.warning("Nenhuma notícia para atualizar status.")
        return
    try:
        query = text("""
            UPDATE relevant_news
            SET status = :status, last_sent_at = :last_sent_at
            WHERE id = ANY(:news_ids)
        """)
        db.execute(query, {"status": status, "last_sent_at": now, "news_ids": news_ids})
        db.commit()
        logger.info(f"Atualizado status para '{status}' e last_sent_at para {len(news_ids)} notícias.")
    except Exception as e:
        logger.error(f"Erro ao atualizar status das notícias: {e}")
        db.rollback()
    finally:
        db.close()