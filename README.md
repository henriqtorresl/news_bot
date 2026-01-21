# News Bot

## Configurar ambiente

1. **Crie o ambiente virtual (venv):**

   No terminal, execute:

   ```bash
   python -m venv venv
   ```

2. **Ative o ambiente virtual:**

   No Windows:

   ```bash
   .\venv\Scripts\activate
   ```

   No Linux/Mac:

   ```bash
   source venv/bin/activate
   ```

3. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente:**

   É necessário criar o arquivo `.env` na raiz do projeto com as variáveis de ambiente. Você pode usar o arquivo `.env.example` como referência, copiando e preenchendo os valores necessários:

   ```bash
   cp .env.example .env
   ```

   Depois, edite o `.env` e preencha os valores das APIs, e-mail e banco conforme sua necessidade.

5. **Execute o projeto:**

   ```bash
   python main.py
   ```

Pronto! O projeto estará rodando.
