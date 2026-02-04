from app.config.logs import logger
from app.config.database import test_connection


if __name__ == "__main__":
    try:
        print("\n==============================\nINICIANDO SCHEDULE DE TESTE\n==============================")
        
        connection = test_connection()
        if connection is False:
            raise Exception("Falha na conexão com o banco de dados.")
        
        print('Teste funcionou!')
        
    except Exception as e:
        logger.error(f"\n[ERRO FATAL] Erro ao rodar schedule de teste: {e}\n")
