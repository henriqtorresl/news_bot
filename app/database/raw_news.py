from sqlalchemy import text

from app.config.database import Session
from app.config.logs import logger


def insert_raw_news(news_item):
	db = Session()
	query = text("""
		INSERT INTO raw_news (published_at, title, source, url, search_engine, raw_content)
		VALUES (:published_at, :title, :source, :url, :search_engine, :raw_content)
		ON CONFLICT (url) DO NOTHING
	""")
	try:
		result = db.execute(query, news_item)
		db.commit()
		if result.rowcount > 0:
			logger.info(f"Notícia inserida: {news_item['title']} ({news_item['url']})")
			return True
		else:
			logger.info(f"Notícia duplicada ignorada: {news_item['title']} ({news_item['url']})")
			return False
	except Exception as e:
		logger.error(f"Erro ao inserir notícia: {e} | URL: {news_item.get('url')}")
		db.rollback()
		return False
	finally:
		db.close()


def get_unclassified_news():
	db = Session()
	query = text("""
		SELECT id, raw_content, url FROM raw_news WHERE is_relevant IS NULL
	""")
	try:
		result = db.execute(query)
		news = [dict(row._mapping) for row in result]
		logger.info(f"{len(news)} notícias não classificadas encontradas.")
		return news
	except Exception as e:
		logger.error(f"Erro ao buscar notícias não classificadas: {e}")
		return []
	finally:
		db.close()


def update_news_relevance(news_id, relevance, context):
	db = Session()
	is_relevant = relevance is not None and relevance >= 7
	query = text("""
		UPDATE raw_news SET is_relevant = :is_relevant, relevance_score = :relevance, context = :context WHERE id = :news_id
	""")
	try:
		db.execute(query, {"is_relevant": is_relevant, "relevance": relevance, "context": context, "news_id": news_id})
		db.commit()
		logger.info(f"Notícia id={news_id} atualizada com relevância={relevance}, is_relevant={is_relevant} e contexto.")
	except Exception as e:
		logger.error(f"Erro ao atualizar relevância da notícia id={news_id}: {e}")
		db.rollback()
	finally:
		db.close()


def get_relevant_news():
	db = Session()
	query = text("""
		SELECT * FROM raw_news rn
		WHERE is_relevant = true
		AND NOT EXISTS (
			SELECT 1 FROM relevant_news r
			WHERE r.original_url = rn.url
		)
	""")
	try:
		result = db.execute(query)
		news = [dict(row._mapping) for row in result]
		logger.info(f"{len(news)} notícias relevantes não agrupadas encontradas.")
		return news
	except Exception as e:
		logger.error(f"Erro ao buscar notícias relevantes não agrupadas: {e}")
		return []
	finally:
		db.close()


def delete_news(id):
	db = Session()
	query = text("""
		DELETE FROM raw_news WHERE id = :id
	""")
	try:
		db.execute(query, {"id": id})
		db.commit()
		logger.info(f"Notícia id={id} deletada.")
	except Exception as e:
		logger.error(f"Erro ao buscar notícias não classificadas: {e}")
		return []
	finally:
		db.close()