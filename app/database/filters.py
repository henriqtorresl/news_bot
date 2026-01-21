from sqlalchemy import text

from app.config.database import Session
from app.config.logs import logger


def get_filters():
    db = Session()
    query = text("SELECT term FROM filters WHERE is_active = true")
    try:
        result = db.execute(query)
        filters = result.fetchall()
        return [row[0] for row in filters]
    except Exception as e:
        logger.error(f"Erro ao buscar os filtros: {e}")
        return None
    finally:
        db.close()
