import re
from pathlib import Path
from typing import Any, Dict, List, Union

import chardet
import pandas as pd


def detectar_encoding(filepath: Union[Path, str]) -> str:
    with open(filepath, "rb") as f:
        raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    return result["encoding"] or "utf-8"


def detectar_delimitador(filepath: Union[Path, str], encoding: str = None) -> str:
    if encoding is None:
        encoding = detectar_encoding(filepath)

    with open(filepath, "r", encoding=encoding) as f:
        primeira_linha = f.readline()

    delimitadores = [",", ";", "\t", "|"]
    contagens = {d: primeira_linha.count(d) for d in delimitadores}
    if not contagens:
        return ","

    return max(contagens, key=contagens.get)


def carregar_csv(filepath: Union[Path, str]) -> pd.DataFrame:
    encoding = detectar_encoding(filepath)
    delimitador = detectar_delimitador(filepath, encoding)

    try:
        df = pd.read_csv(
            filepath,
            encoding=encoding,
            sep=delimitador,
            engine='python'
        )
        return df
    except Exception as e:
        if encoding.lower() == 'utf-8':
            return pd.read_csv(
                filepath,
                encoding='latin-1',
                sep=delimitador,
                engine='python'
            )
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

    return {
        "valido": len(colunas_faltando) == 0,
        "colunas_faltando": colunas_faltando
    }


def validar_nomes_colunas(df: pd.DataFrame, template: dict) -> dict:
    colunas_presentes = set(df.columns)
    colunas_template = set(template["colunas"].keys())
    mapeamento_sugerido = {}
    colunas_desconhecidas = []

    for col in colunas_presentes:
        if col in colunas_template:
            continue
        encontrado = False
        for nome_template, config in template["colunas"].items():
            if col in config.get("aliases", []):
                mapeamento_sugerido[col] = nome_template
                encontrado = True
                break
        if not encontrado:
            colunas_desconhecidas.append(col)

    return {
        "valido": len(mapeamento_sugerido) == 0,
        "mapeamento_sugerido": mapeamento_sugerido,
        "colunas_desconhecidas": colunas_desconhecidas
    }


def validar_formato_data(df: pd.DataFrame, coluna: str, template: dict) -> dict:
    if coluna not in df.columns:
        return {"valido": False, "formato_detectado": None}
    valores = df[coluna].astype(str)
    matches = valores.str.match(r"^\d{4}-\d{2}-\d{2}$")
    valido = matches.sum() > len(valores) * 0.8

    formato = "YYYY-MM-DD" if valido else "Desconhecido"
    if not valido:
        br_match = valores.str.match(r"^\d{2}/\d{2}/\d{4}$")
        if br_match.sum() > len(valores) * 0.8:
            formato = "DD/MM/YYYY"

    return {
        "valido": valido,
        "formato_detectado": formato,
        "linhas_invalidas": df[~matches].index.tolist()
    }


def validar_formato_valor(df: pd.DataFrame, coluna: str, template: dict) -> dict:
    if coluna not in df.columns:
        return {"valido": False}
    try:
        pd.to_numeric(df[coluna])
        return {"valido": True, "formato_detectado": "decimal"}
    except Exception:
        return {"valido": False, "formato_detectado": "texto_ou_brasileiro"}


def validar_enum(df: pd.DataFrame, coluna: str, template: dict) -> dict:
    if coluna not in df.columns:
        return {"valido": False, "valores_invalidos": []}

    config = template["colunas"].get(coluna, {})
    if "validacao" not in config:
        return {"valido": True}
    if "valores_permitidos" not in config["validacao"]:
        return {"valido": True}

    valores_permitidos = set(config["validacao"]["valores_permitidos"])
    valores_unicos = df[coluna].dropna().unique()
    valores_invalidos = [
        v for v in valores_unicos
        if str(v).upper() not in valores_permitidos
    ]

    return {
        "valido": len(valores_invalidos) == 0,
        "valores_invalidos": valores_invalidos,
        "mapeamento_sugerido": {}
    }


def validar_csv_completo(filepath: Union[Path, str], template: dict) -> dict:
    try:
        df = carregar_csv(filepath)
    except Exception as e:
        return {
            "valido": False,
            "total_erros": 1,
            "detalhes": [{"tipo": "erro_leitura", "mensagem": str(e)}]
        }

    detalhes = []

    res_col = validar_colunas_obrigatorias(df, template)
    if not res_col["valido"]:
        detalhes.append({
            "tipo": "colunas_faltando",
            "colunas": res_col["colunas_faltando"]
        })

    res_nom = validar_nomes_colunas(df, template)
    if not res_nom["valido"]:
        detalhes.append({
            "tipo": "nomes_colunas",
            "mapeamento": res_nom["mapeamento_sugerido"]
        })

    for col, config in template["colunas"].items():
        if col in df.columns:
            tipo_dado = config.get("tipo_dado")

            if tipo_dado == "DATE":
                res_data = validar_formato_data(df, col, template)
                if not res_data["valido"]:
                    detalhes.append({
                        "tipo": "formato_data",
                        "coluna": col,
                        "detectado": res_data["formato_detectado"]
                    })

            elif tipo_dado == "DECIMAL":
                res_valor = validar_formato_valor(df, col, template)
                if not res_valor["valido"]:
                    detalhes.append({
                        "tipo": "formato_valor",
                        "coluna": col,
                        "detectado": res_valor["formato_detectado"]
                    })

            if "validacao" in config:
                if "valores_permitidos" in config["validacao"]:
                    res_enum = validar_enum(df, col, template)
                    if not res_enum["valido"]:
                        detalhes.append({
                            "tipo": "valor_invalido",
                            "coluna": col,
                            "valores": res_enum["valores_invalidos"]
                        })

    return {
        "valido": len(detalhes) == 0,
        "total_erros": len(detalhes),
        "detalhes": detalhes
    }


def gerar_relatorio_divergencias(filepath: Union[Path, str], template: dict) -> str:
    res = validar_csv_completo(filepath, template)
    if res["valido"]:
        return "Nenhuma divergencia."

    msg = []
    for erro in res["detalhes"]:
        if erro["tipo"] == "colunas_faltando":
            cols = ', '.join(erro['colunas'])
            msg.append(f"Colunas faltando: {cols}")
        elif erro["tipo"] == "nomes_colunas":
            msg.append(f"Colunas com nome errado: {erro['mapeamento']}")
        elif erro["tipo"] == "erro_leitura":
            msg.append(f"Erro fatal de leitura: {erro['mensagem']}")
        elif erro["tipo"] == "formato_data":
            dt = erro['detectado']
            msg.append(f"Coluna '{erro['coluna']}' data inválida. Parece: {dt}")
        elif erro["tipo"] == "formato_valor":
            msg.append(f"Coluna '{erro['coluna']}' tem valores não numéricos.")
        elif erro["tipo"] == "valor_invalido":
            val = erro['valores']
            msg.append(f"Coluna '{erro['coluna']}' valores não permitidos: {val}")

    return "\n".join(msg)