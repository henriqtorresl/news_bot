import os
from dotenv import load_dotenv

load_dotenv()

class Environments:
    # API Keys
    GOOGLE_NEWS_API_KEY = os.getenv("GOOGLE_NEWS_API_KEY")
    BING_NEWS_API_KEY = os.getenv("BING_NEWS_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ALERTA_LICITACAO_API_KEY = os.getenv("ALERTA_LICITACAO_API_KEY")
    
    # E-mail
    MAIL_USER = os.getenv("MAIL_USER")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
env = Environments()