import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database", "data_pipeline.db")

def conexao_banco():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calcular_hash_estrutura(df: pd.DataFrame) -> str:
    colunas = sorted(list(df.columns))
    assinatura = ",".join(colunas)
    return hashlib.md5(assinatura.encode()).hexdigest()

def buscar_script_por_hash(hash_estrutura: str):
    conn = conexao_banco()
    script = conn.execute(
        "SELECT * FROM scripts_transformacao WHERE hash_estrutura = ?", 
        (hash_estrutura,)
    ).fetchone()
    conn.close()
    return script

def salvar_script(hash_estrutura: str, script_python: str):
    conn = conexao_banco()
    try:
        conn.execute(
            "INSERT INTO scripts_transformacao (hash_estrutura, script_python) VALUES (?, ?)",
            (hash_estrutura, script_python)
        )
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE scripts_transformacao SET script_python = ?, updated_at = ? WHERE hash_estrutura = ?",
            (script_python, datetime.now(), hash_estrutura)
        )
    conn.commit()
    conn.close()

def registrar_log(arquivo_nome, total, sucesso, erro, usou_ia, script_id, duracao):
    conn = conexao_banco()
    conn.execute(
        """
        INSERT INTO log_ingestao 
        (arquivo_nome, registros_total, registros_sucesso, registros_erro, usou_ia, script_id, duracao_segundos)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (arquivo_nome, total, sucesso, erro, usou_ia, script_id, duracao)
    )
    conn.commit()
    conn.close()