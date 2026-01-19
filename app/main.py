import streamlit as st
import pandas as pd
import json
import tempfile
import os
import sys
import time
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.validation import validar_csv_completo, carregar_csv, gerar_relatorio_divergencias
from src.ai_handler import gerar_script_correcao
from src.db_handler import calcular_hash_estrutura, buscar_script_por_hash, salvar_script, registrar_log

st.set_page_config(page_title="Validador Financeiro AI", page_icon="🤖", layout="wide")

st.title("Pipeline de Ingestão Inteligente")
st.markdown("Upload -> Validação -> Correção via IA (ou Cache) -> Ingestão")

try:
    with open("database/template.json", "r", encoding="utf-8") as f:
        template = json.load(f)
except FileNotFoundError:
    st.error("Template não encontrado.")
    st.stop()

uploaded_file = st.file_uploader("Arraste seu CSV", type=["csv"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded_file.getbuffer())
        input_path = tmp.name

    col1, col2 = st.columns(2)
    
    try:
        df_raw, encoding = carregar_csv(input_path)
        file_hash = calcular_hash_estrutura(df_raw)
        
        with col1:
            st.subheader("Arquivo Original")
            st.dataframe(df_raw.head())
            st.info(f"Encoding: {encoding} | Linhas: {len(df_raw)} | Hash: {file_hash[:8]}...")
            
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        st.stop()

    resultado = validar_csv_completo(input_path, template)
    
    with col2:
        st.subheader("Diagnóstico")
        if resultado["valido"]:
            st.success("Arquivo Perfeito! Pronto para ingestão.")
        else:
            st.error(f"{resultado['total_erros']} problemas detectados.")
            erros_texto = gerar_relatorio_divergencias(input_path, template)
            with st.expander("Ver detalhes dos erros"):
                st.text(erros_texto)

            st.subheader("Motor de Correção")
            script_db = buscar_script_por_hash(file_hash)
            script_content = ""
            fonte_script = ""

            if script_db:
                st.success("Script encontrado no CACHE!")
                script_content = script_db["script_python"]
                fonte_script = "cache"
            else:
                st.warning("Estrutura desconhecida. Acionando IA...")
                if st.button("Gerar Script de Correção"):
                    with st.spinner("A IA está trabalhando..."):
                        with open(input_path, "r", encoding=encoding) as f:
                            amostra = "".join(f.readlines()[:5])
                        script_content = gerar_script_correcao(erros_texto, amostra, template)
                        fonte_script = "ia"
                        if not script_content:
                            st.error("Falha ao gerar script.")

            if script_content:
                st.text_area("Script Python", script_content, height=200, key="editor_script")
                if st.button("Executar e Validar Correção"):
                    output_path = input_path.replace(".csv", "_fixed.csv")
                    try:
                        start_time = time.time()
                        local_scope = {}
                        exec(st.session_state["editor_script"], {}, local_scope)
                        if "processar_csv" not in local_scope:
                            raise Exception("O script não criou a função 'processar_csv(input, output)'!")
                        processar_csv = local_scope["processar_csv"]
                        processar_csv(input_path, output_path)
                        duration = time.time() - start_time
                        st.markdown("---")
                        st.subheader("Resultado da Correção")
                        df_fixed, _ = carregar_csv(output_path)
                        st.dataframe(df_fixed.head())
                        novo_resultado = validar_csv_completo(output_path, template)
                        if novo_resultado["valido"]:
                            st.success(f"SUCESSO! Validado em {duration:.2f}s.")
                            if fonte_script == "ia" or fonte_script == "":
                                salvar_script(file_hash, st.session_state["editor_script"])
                                st.toast("Script salvo!", icon="")
                            registrar_log(uploaded_file.name, len(df_fixed), len(df_fixed), 0, fonte_script=="ia", 1, duration)
                        else:
                            st.error("O script rodou, mas o arquivo ainda tem erros.")
                            st.text(gerar_relatorio_divergencias(output_path, template))
                    except Exception as e:
                        st.error(f"Erro na execução: {str(e)}")
                        st.code(traceback.format_exc())