import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def gerar_script_correcao(erros_texto, amostra_csv, template):
    colunas_alvo = ", ".join(template['colunas'].keys())
    
    prompt = f"""
    Atue como um Engenheiro de Dados Sênior Especialista em Pandas.
    
    OBJETIVO:
    Gerar uma função Python chamada `processar_csv(input_path, output_path)` que transforma um CSV sujo para o formato padrão.
    
    O SCHEMA ALVO (Obrigatório) deve ter estas colunas exatas:
    [{colunas_alvo}]
    
    PROBLEMAS DETECTADOS NO ARQUIVO:
    {erros_texto}
    
    AMOSTRA DOS DADOS (Primeiras 5 linhas):
    {amostra_csv}
    
    REGRAS RÍGIDAS:
    1. Importe pandas as pd.
    2. Leia o CSV detectando o encoding correto (tente 'utf-8', se falhar 'latin-1') e o delimitador correto (',' ou ';').
    3. Renomeie as colunas para bater com o SCHEMA ALVO. Exemplo: se vier 'Date', renomeie para 'data_transacao'.
    4. Trate datas: converta para YYYY-MM-DD. Se a data for inválida, transforme em NaT.
    5. Trate valores numéricos (R$): remova 'R$', converta vírgula decimal para ponto. Transforme em float.
    6. Salve o arquivo final em `output_path` com encoding='utf-8' e index=False.
    7. NÃO use blocos de código markdown (```python). Retorne APENAS o código puro.
    8. A função deve ser robusta: use try/except onde necessário.
    
    Retorne APENAS o código Python, nada mais.
    """
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    try:
        response = model.generate_content(prompt)
        codigo = response.text.replace("```python", "").replace("```", "").strip()
        return codigo
    except Exception as e:
        print(f"Erro na IA: {e}")
        return None