"""
Fixtures compartilhadas para os testes do CSV Validator.
NAO MODIFIQUE ESTE ARQUIVO - ele faz parte do desafio.
"""
import json
import os
import sqlite3
import tempfile
from pathlib import Path
import pytest

# Diretorio raiz do projeto
ROOT_DIR = Path(__file__).parent.parent
SAMPLE_DATA_DIR = ROOT_DIR / "sample_data"
DATABASE_DIR = ROOT_DIR / "database"

@pytest.fixture
def template_schema():
    template_path = DATABASE_DIR / "template.json"
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def db_connection():
    conn = sqlite3.connect(":memory:")
    schema_path = DATABASE_DIR / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()

@pytest.fixture
def sample_csv_perfeito(): return SAMPLE_DATA_DIR / "perfeito.csv"
@pytest.fixture
def sample_csv_colunas_extras(): return SAMPLE_DATA_DIR / "colunas_extras.csv"
@pytest.fixture
def sample_csv_colunas_faltando(): return SAMPLE_DATA_DIR / "colunas_faltando.csv"
@pytest.fixture
def sample_csv_nomes_diferentes(): return SAMPLE_DATA_DIR / "nomes_diferentes.csv"
@pytest.fixture
def sample_csv_formato_data_br(): return SAMPLE_DATA_DIR / "formato_data_br.csv"
@pytest.fixture
def sample_csv_formato_valor_br(): return SAMPLE_DATA_DIR / "formato_valor_br.csv"
@pytest.fixture
def sample_csv_encoding_latin1(): return SAMPLE_DATA_DIR / "encoding_latin1.csv"
@pytest.fixture
def sample_csv_delimitador_pv(): return SAMPLE_DATA_DIR / "delimitador_pv.csv"
@pytest.fixture
def sample_csv_multiplos_problemas(): return SAMPLE_DATA_DIR / "multiplos_problemas.csv"

@pytest.fixture
def temp_output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)