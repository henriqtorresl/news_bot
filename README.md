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

## Automação (GitHub Actions)

Embora o comando `python main.py` execute toda a pipeline localmente para testes, em ambiente de produção a lógica é dividida em dois fluxos automatizados via **GitHub Actions**, garantindo que o processamento e o disparo ocorram em horários estratégicos:

### 1. Sincronização e Processamento (`sync_news.yml`)

Este workflow é responsável pelas etapas de **Busca (Crawler)**, **Classificação (AI)** e **Agrupamento** das notícias no banco de dados.

- **Frequência:** 2 vezes ao dia.
- **Horários:** 06:00 e 18:00 (Horário de Brasília).
- **Script executado:** `app/schedules/sync_news.py`

### 2. Disparo de Newsletter (`send_newsletter.yml`)

Este workflow filtra as notícias relevantes processadas que ainda não foram enviadas e realiza o disparo do e-mail para os usuários.

- **Frequência:** 1 vez ao dia.
- **Horário:** 08:00 (Horário de Brasília).
- **Script executado:** `app/schedules/send_newsletter.py`

> **Nota:** Os horários nos arquivos YAML estão configurados em **UTC** (09:00, 21:00 e 11:00, respectivamente) para corresponderem ao fuso horário de Brasília (UTC-3).
