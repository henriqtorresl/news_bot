from app.config.logs import logger
from app.config.database import test_connection
from app.services.news_crawler import process_news
from app.services.news_classifier import classify_and_update_all
from app.services.news_grouping import process_and_save_relevant_news
from app.services.email_sender import send_newsletter_email


if __name__ == "__main__":
    try:
        print("\n==============================\nINICIANDO PIPELINE DE NOTÍCIAS\n==============================")
        
        connection = test_connection()
        if connection is False:
            raise Exception("Falha na conexão com o banco de dados.")

        print("\n=== ETAPA 1: Busca de notícias ===\n")
        process_news(max_news=100)

        print("\n=== ETAPA 2: Classificação de notícias ===\n")
        classify_and_update_all()

        print("\n=== ETAPA 3: Agrupamento e inserção das notícias relevantes ===\n")
        process_and_save_relevant_news()

        print("\n=== ETAPA 4: Disparo de e-mail com resumos ===\n")
        send_newsletter_email()

        print("\n==============================\nPIPELINE FINALIZADO COM SUCESSO\n==============================\n")
    except Exception as e:
        logger.error(f"\n[ERRO FATAL] Erro ao rodar o bot de notícias: {e}\n")
