import re
from pathlib import Path
from typing import Any
import chardet
import pandas as pd

def detectar_encoding(filepath: Path | str) -> str:
    with open(filepath, "rb") as f:
        raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    return result["encoding"] or "utf-8"

def detectar_delimitador(filepath: Path | str, encoding: str = None) -> str:
    if encoding is None:
        encoding = detectar_encoding(filepath)

    with open(filepath, "r", encoding=encoding) as f:
        primeira_linha = f.readline()

    delimitadores = [",", ";", "\t", "|"]
    contagens = {d: primeira_linha.count(d) for d in delimitadores}

    if not contagens:
        return ","
    return max(contagens, key=contagens.get)

def carregar_csv(filepath: Path | str) -> tuple[pd.DataFrame, str]:
    encoding = detectar_encoding(filepath)
    delimitador = detectar_delimitador(filepath, encoding)
    try:
        df = pd.read_csv(filepath, encoding=encoding, sep=delimitador, engine='python')
        return df, encoding
    except Exception as e:
        if encoding.lower() == 'utf-8':
            return pd.read_csv(filepath, encoding='latin-1', sep=delimitador, engine='python'), 'latin-1'
        raise e

def validar_colunas_obrigatorias(df: pd.DataFrame, template: dict) -> dict:
    colunas_obrigatorias = [
        nome for nome, config in template["colunas"].items()
        if config.get("obrigatorio", False)
    ]
    colunas_presentes = set(df.columns)
    colunas_faltando = []

    for col in colunas_obrigatorias:
        if col not in colunas_presentes:
            aliases = template["colunas"][col].get("aliases", [])
            if not any(alias in colunas_presentes for alias in aliases):
                colunas_faltando.append(col)

    return {"valido": len(colunas_faltando) == 0, "colunas_faltando": colunas_faltando}

def validar_nomes_colunas(df: pd.DataFrame, template: dict) -> dict:
    colunas_presentes = set(df.columns)
    colunas_template = set(template["colunas"].keys())
    mapeamento_sugerido = {}
    colunas_desconhecidas = []

    for col in colunas_presentes:
        if col in colunas_template: continue
        encontrado = False
        for nome_template, config in template["colunas"].items():
            if col in config.get("aliases", []):
                mapeamento_sugerido[col] = nome_template
                encontrado = True
                break
        if not encontrado:
            colunas_desconhecidas.append(col)

    return {"valido": len(mapeamento_sugerido) == 0, "mapeamento_sugerido": mapeamento_sugerido, "colunas_desconhecidas": colunas_desconhecidas}

def validar_formato_data(df: pd.DataFrame, coluna: str, template: dict) -> dict:
    if coluna not in df.columns: return {"valido": False, "formato_detectado": None}
    valores = df[coluna].astype(str)
    matches = valores.str.match(r"^\d{4}-\d{2}-\d{2}$")
    valido = matches.sum() > len(valores) * 0.8
    return {"valido": valido, "formato_detectado": "YYYY-MM-DD" if valido else "Desconhecido"}

def validar_formato_valor(df: pd.DataFrame, coluna: str, template: dict) -> dict:
    if coluna not in df.columns: return {"valido": False}
    try:
        pd.to_numeric(df[coluna])
        return {"valido": True, "formato_detectado": "decimal"}
    except:
        return {"valido": False, "formato_detectado": "texto/brasileiro"}

def validar_csv_completo(filepath: Path | str, template: dict) -> dict:
    try:
        resultado_load = carregar_csv(filepath)
        if isinstance(resultado_load, tuple):
            df = resultado_load[0]
        else:
            df = resultado_load
    except Exception as e:
        return {"valido": False, "total_erros": 1, "detalhes": [{"tipo": "erro_leitura", "mensagem": str(e)}]}

    detalhes = []

    res_col = validar_colunas_obrigatorias(df, template)
    if not res_col["valido"]:
        detalhes.append({"tipo": "colunas_faltando", "colunas": res_col["colunas_faltando"]})

    res_nom = validar_nomes_colunas(df, template)
    if not res_nom["valido"]:
        detalhes.append({"tipo": "nomes_colunas", "mapeamento": res_nom["mapeamento_sugerido"]})
    return {
        "valido": len(detalhes) == 0,
        "total_erros": len(detalhes),
        "detalhes": detalhes
    }

def gerar_relatorio_divergencias(filepath: Path | str, template: dict) -> str:
    res = validar_csv_completo(filepath, template)
    if res["valido"]: return "Arquivo válido."
    msg = []
    for erro in res["detalhes"]:
        if erro["tipo"] == "colunas_faltando":
            msg.append(f"Colunas faltando: {', '.join(erro['colunas'])}")
        elif erro["tipo"] == "nomes_colunas":
            msg.append(f"Colunas com nome errado: {erro['mapeamento']}")
        elif erro["tipo"] == "erro_leitura":
            msg.append(f"Erro fatal de leitura: {erro['mensagem']}")
    return "\n".join(msg)