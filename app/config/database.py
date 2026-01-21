from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.environments import env
from app.config.logs import logger

engine = create_engine(
    env.DATABASE_URL,
    echo=False
)

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_connection():
    try:
        with engine.connect() as conn:
            logger.info("✅ Conexão com o PostgreSQL estabelecida com sucesso!")
            return True
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco de dados: {e}")
        return False