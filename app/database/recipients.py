from sqlalchemy import text

from app.config.database import Session
from app.config.logs import logger


def get_recipient_emails():
    db = Session()
    query = text("SELECT email FROM recipients WHERE is_active = true")
    try:
        result = db.execute(query)
        recipients = result.fetchall()
        return [row[0] for row in recipients]
    except Exception as e:
        logger.error(f"Erro ao buscar os emails dos destinatários: {e}")
        return None
    finally:
        db.close()
