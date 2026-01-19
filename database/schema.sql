-- Schema do banco de dados para o desafio CSV Validator

CREATE TABLE IF NOT EXISTS transacoes_financeiras (
    id_transacao TEXT PRIMARY KEY,
    data_transacao DATE NOT NULL,
    valor DECIMAL(15, 2) NOT NULL CHECK (valor > 0),
    tipo TEXT NOT NULL CHECK (tipo IN ('CREDITO', 'DEBITO')),
    categoria TEXT NOT NULL CHECK (categoria IN (
        'SALARIO', 'ALIMENTACAO', 'TRANSPORTE', 'MORADIA', 'SAUDE',
        'EDUCACAO', 'LAZER', 'INVESTIMENTO', 'TRANSFERENCIA', 'OUTROS'
    )),
    descricao TEXT,
    conta_origem TEXT NOT NULL,
    conta_destino TEXT,
    status TEXT NOT NULL DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE', 'CONFIRMADO', 'CANCELADO')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_data_transacao ON transacoes_financeiras(data_transacao);
CREATE INDEX IF NOT EXISTS idx_categoria ON transacoes_financeiras(categoria);

CREATE TABLE IF NOT EXISTS scripts_transformacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash_estrutura TEXT UNIQUE NOT NULL,
    script_python TEXT NOT NULL,
    descricao TEXT,
    vezes_utilizado INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS log_ingestao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arquivo_nome TEXT NOT NULL,
    registros_total INTEGER,
    registros_sucesso INTEGER,
    registros_erro INTEGER,
    usou_ia BOOLEAN DEFAULT FALSE,
    script_id INTEGER REFERENCES scripts_transformacao(id),
    duracao_segundos REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);