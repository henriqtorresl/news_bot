from app.config.logs import logger
from app.config.database import test_connection
from app.services.email_sender import send_newsletter_email
from app.database.recipients import get_recipients


if __name__ == "__main__":
    try:
        print("\n==============================\nINICIANDO PIPELINE DE DISPARO DE NOTÍCIAS RELEVANTES\n==============================")
        
        connection = test_connection()
        if connection is False:
            raise Exception("Falha na conexão com o banco de dados.")

        print("\n=== Disparo de e-mail com resumos ===\n")
        send_newsletter_email()

        recipients = get_recipients()
        if recipients:
            logger.info("Usuário(s) notificado(s):")
            for name, email in recipients:
                logger.info(f"- {name} <{email}>")

        print("\n==============================\nPIPELINE FINALIZADO COM SUCESSO\n==============================\n")
    except Exception as e:
        logger.error(f"Erro ao disparar os emails com as notícias: {e}\n")
