-- 1. Tabela de Filtros
CREATE TABLE filters (
    id SERIAL PRIMARY KEY,
    term VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela de Destinatários (Gestão da Newsletter)
CREATE TABLE recipients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- 3. Tabela de Notícias Brutas
CREATE TABLE raw_news (
    id SERIAL PRIMARY KEY,
    published_at TIMESTAMP,
    title TEXT NOT NULL,
    source VARCHAR(255),
    url TEXT UNIQUE NOT NULL, -- UNIQUE para evitar duplicidade na captura
    search_engine VARCHAR(50),    -- 'google_news', 'bing_news', 'portal_compras'
    raw_content TEXT,
    is_relevant BOOLEAN, -- Definido pelo Serviço de Classificação, nota de relevancia >= 7
    relevance_score INT, -- Nota de relevância atribuída pela IA
    context TEXT, -- Contexto gerado pela IA
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabela de Notícias Relevantes (A Curadoria para Envio)
CREATE TABLE relevant_news (
    id SERIAL PRIMARY KEY,
    original_url TEXT UNIQUE NOT NULL, -- Chave estrangeira lógica para raw_news.url
    published_at TIMESTAMP,
    original_title TEXT,
    source VARCHAR(255),
    topic VARCHAR(255),          -- Agrupamento gerado pela IA
    headline TEXT,               -- Headline resumida pela IA
    ai_summary TEXT,             -- Resumo de até 250 tokens
    status VARCHAR(20) DEFAULT 'pending', -- Status do grupo relevante (novo campo)
    last_sent_at TIMESTAMP,      -- Se NULL, ainda não foi enviada
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_raw_news FOREIGN KEY (original_url) REFERENCES raw_news(url)
);