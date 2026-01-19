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
from src.db_handler import calcular_hash_estrutura, buscar_script_por_hash, salvar_script, registrar_log, ingestar_transacoes

st.set_page_config(page_title="Validador Financeiro AI", layout="wide")

st.title("Pipeline de Ingestão Inteligente")
st.markdown("Upload -> Validação -> Correção via IA (ou Cache) -> Ingestão")

if "script_atual" not in st.session_state:
    st.session_state["script_atual"] = ""
if "fonte_script" not in st.session_state:
    st.session_state["fonte_script"] = ""

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
            if st.button("💾 Ingestar no Banco de Dados"):
                try:
                    ingestar_transacoes(df_raw)
                    st.success(f"Sucesso! {len(df_raw)} transações salvas no banco.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")
            st.session_state["script_atual"] = ""
        else:
            st.error(f"{resultado['total_erros']} problemas detectados.")
            erros_texto = gerar_relatorio_divergencias(input_path, template)
            with st.expander("Ver detalhes dos erros"):
                st.text(erros_texto)

            st.subheader("Motor de Correção")
            script_db = buscar_script_por_hash(file_hash)
            if script_db:
                if st.session_state["script_atual"] == "" or st.session_state["fonte_script"] != "cache":
                     st.session_state["script_atual"] = script_db["script_python"]
                     st.session_state["fonte_script"] = "cache"
                st.success("Script encontrado no CACHE!")
            elif st.session_state["script_atual"] == "":
                st.warning("Estrutura desconhecida. Acionando IA...")
                if st.button("Gerar Script de Correção"):
                    with st.spinner("A IA está trabalhando..."):
                        with open(input_path, "r", encoding=encoding) as f:
                            amostra = "".join(f.readlines()[:5])
                        novo_script = gerar_script_correcao(erros_texto, amostra, template)
                        if novo_script:
                            st.session_state["script_atual"] = novo_script
                            st.session_state["fonte_script"] = "ia"
                            st.rerun()
                        else:
                            st.error("Falha ao gerar script.")

            if st.session_state["script_atual"]:
                st.markdown("### Editor de Script")
                script_editado = st.text_area(
                    "Script Python", 
                    value=st.session_state["script_atual"], 
                    height=300,
                    key="editor_key"
                )
                st.session_state["script_atual"] = script_editado

                if st.button("Executar e Validar Correção"):
                    output_path = input_path.replace(".csv", "_fixed.csv")
                    try:
                        start_time = time.time()
                        local_scope = {}
                        exec(script_editado, local_scope)
                        if "processar_csv" not in local_scope:
                            st.error("ERRO: A IA não criou a função 'processar_csv'. Gere novamente.")
                            st.stop()
                        processar_csv = local_scope["processar_csv"]
                        processar_csv(input_path, output_path)
                        duration = time.time() - start_time
                        st.markdown("---")
                        st.subheader("Resultado da Correção")
                        if not os.path.exists(output_path):
                            st.error("O script rodou mas não criou o arquivo de saída.")
                            st.stop()

                        df_fixed, _ = carregar_csv(output_path)
                        st.dataframe(df_fixed.head())
                        novo_resultado = validar_csv_completo(output_path, template)
                        if novo_resultado["valido"]:
                            st.success(f"Validado em {duration:.2f}s. Salvando no banco...")
                            if st.session_state["fonte_script"] == "ia":
                                salvar_script(file_hash, script_editado)
                            registrar_log(uploaded_file.name, len(df_fixed), len(df_fixed), 0, st.session_state["fonte_script"]=="ia", 1, duration)
                            ingestar_transacoes(df_fixed)
                            st.toast("Dados salvos na tabela transacoes_financeiras!", icon="🏦")
                            st.balloons()
                        else:
                            st.warning(f"O script rodou, mas sobraram {novo_resultado['total_erros']} erros.")
                            st.text(gerar_relatorio_divergencias(output_path, template))
                    except Exception as e:
                        st.error(f"Erro fatal na execução: {str(e)}")
                        st.code(traceback.format_exc())