import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError("A chave GEMINI_API_KEY não foi encontrada! Verifique seu arquivo .env")

genai.configure(api_key=api_key)

def gerar_script_correcao(erros_relatorio: str, amostra_csv: str, template_json: dict) -> str:
    """
    Envia os erros e a amostra de dados para o Gemini e solicita um script Python de correção.
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""
    You are a Senior Data Engineer. I have a CSV file with data quality issues.
    Your task is to generate a Python script to fix these issues and standardize the data.

    CONTEXT:
    The CSV file has the following detected errors:
    {erros_relatorio}

    TARGET SCHEMA (JSON):
    {template_json}

    SAMPLE DATA (First 5 lines of input):
    {amostra_csv}

    INSTRUCTIONS:
    1. Write a Python script using 'pandas'.
    2. The script must define a function called 'processar_csv(input_path, output_path)'.
    3. Read the CSV using 'input_path'. Handle encoding if necessary (try 'utf-8' then 'latin-1').
    4. Fix ALL mentioned errors (rename columns, convert dates to YYYY-MM-DD, clean currency symbols like 'R$', convert to float).
    5. Ensure the final DataFrame matches the 'TARGET SCHEMA' exactly.
    6. Save the result to 'output_path' (CSV, utf-8, no index).
    7. Return ONLY the raw Python code. Do NOT use markdown blocks (```python). Do NOT add explanations.
    """

    try:
        response = model.generate_content(prompt)
        codigo_gerado = response.text
        codigo_gerado = codigo_gerado.replace("```python", "").replace("```", "").strip()
        return codigo_gerado
    except Exception as e:
        print(f"Erro ao chamar a IA: {e}")
        return None


if __name__ == "__main__":
    print("Módulo de IA configurado. Testando conexão...")
    try:
        # Teste simples de 'ping' na IA
        model = genai.GenerativeModel('gemini-2.5-flash')
        res = model.generate_content("Say 'Hello Data Engineer!'")
        print(f"Resposta da IA: {res.text}")
    except Exception as e:
        print(f"Erro de conexão: {e}")

