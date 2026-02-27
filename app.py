import streamlit as st
import os
import pandas as pd
from pipeline_manager import PipelineManager
import asyncio
import tempfile

st.set_page_config(page_title="Perazzo Vision 2.1", page_icon="⚖️", layout="wide")

# CSS customizado para dar um ar mais Premium (Painel Jurídico)
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #1f77b4;
    }
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>⚖️ Perazzo Vision 2.1 - Central de Triagem Franco-Atiradora</h1>", unsafe_allow_html=True)

if 'pipeline' not in st.session_state:
    st.session_state.pipeline = PipelineManager()

# A "Barra da Mira" do Franco Atirador
st.markdown("### 🎯 1. Definir Alvo da Pesquisa")
nome_alvo = st.text_input("Qual o nome do cliente cujos extratos estamos procurando?", 
                         placeholder="Ex: AMARO AMARAL SILVA", 
                         help="O sistema ignorará extratos da conta de qualquer outra pessoa.")

st.markdown("---")

col_fila, col_metricas = st.columns([1, 2])

with col_fila:
    st.subheader("📂 2. Anexar Processo PJe (PDF)")
    
    arquivo_upado = st.file_uploader("Arraste e solte o PDF do processo (pode ter 300+ págs)", type=["pdf"])
    
    pode_iniciar = arquivo_upado is not None and len(nome_alvo.strip()) > 3
    
    btn_iniciar = st.button("🚀 3. INICIAR CAÇADA", type="primary", use_container_width=True, disabled=not pode_iniciar)
    if not pode_iniciar:
        st.caption("Preencha o nome do cliente E faça o upload do PDF para liberar a caçada.")

with col_metricas:
    st.subheader("🖥️ Monitor da Esteira")
    container_logs = st.empty()
    
    if btn_iniciar and arquivo_upado is not None:
        with st.spinner(f"Processando Dossiê de '{nome_alvo}'... Isso pode levar alguns minutos (Arquitetura Nuvem)."):
            # ARQUITETURA CLOUD NATIVE: Uso de Tempfile descartável ao invés de disco físico "C:/"
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(arquivo_upado.getbuffer())
                    caminho_salvo = tmp_file.name
                    
                # Dispara a maquina assincrona real focada neste unico arquivo
                relatorio = asyncio.run(st.session_state.pipeline.rodar_processo_unico(caminho_pdf=caminho_salvo, nome_alvo=nome_alvo))
                st.session_state.ultimo_relatorio = relatorio
                
                # Faxina Cloud (Não deixa rastro pra nao estourar espaço do servidor grátis)
                try: os.unlink(caminho_salvo) 
                except Exception as del_err: print(f"Aviso de permissão ao deletar tempfile: {del_err}")
                
                container_logs.success("✅ Busca Finalizada com Sucesso!")
            except Exception as e:
                container_logs.error(f"Erro fatal no motor principal: {e}")

# SEÇÃO DE RESULTADOS (Surge após processar)
if 'ultimo_relatorio' in st.session_state:
    st.markdown("---")
    st.subheader("📊 Resultados da Caçada")
    
    relatorio = st.session_state.ultimo_relatorio
    elegiveis = relatorio.get("elegiveis", [])
    descartados = relatorio.get("descartados", [])
    dossie_path = relatorio.get("dossie_path")
    
    # KPIs Rápidos
    m1, m2, m3 = st.columns(3)
    m1.metric("Extratos Válidos do Cliente", len(elegiveis))
    m2.metric("Páginas/Extratos Descartadas", len(descartados))
    
    total_grana = sum(e.get("saldo_anterior_base_ajustado", 0) for e in elegiveis)
    m3.metric("Valor Base Encontrado", f"R$ {total_grana:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    # O BOTÃO MAIS IMPORTANTE: Download do Dossiê
    if dossie_path and os.path.exists(dossie_path):
        st.success(f"📚 Dossiê compilado! {len(elegiveis)} páginas relevantes unificadas.")
        with open(dossie_path, "rb") as pdf_file:
            st.download_button(
                label="📥 BAIXAR DOSSIÊ DO CLIENTE (PDF)",
                data=pdf_file,
                file_name=os.path.basename(dossie_path),
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            
    # Relatórios Analíticos em Abas
    tab_sucesso, tab_lixo = st.tabs(["✅ Aprovados (No Dossiê)", "🗑️ Lixeira (Por quê?)"])
    
    with tab_sucesso:
        if elegiveis:
            df_sucesso = pd.DataFrame(elegiveis)[["arquivo_origem", "titular", "banco", "conta", "periodo_extrato", "saldo_anterior_base_ajustado"]]
            df_sucesso.columns = ["Arquivo Fonte", "Titular Lido", "Banco", "Conta", "Período", "Saldo-Base (Ajustado)"]
            st.dataframe(df_sucesso, use_container_width=True)
        else:
            st.info("Nenhum extrato válido encontrado para este cliente.")
            
    with tab_lixo:
        if descartados:
            df_lixo = pd.DataFrame(descartados)
            # Tentar garimpar o motivo e arquivo, já que alguns lixos básicos vêm com chaves limitadas do Gemini
            cols_exibicao = []
            if "arquivo_origem" in df_lixo.columns: cols_exibicao.append("arquivo_origem")
            if "titular" in df_lixo.columns: cols_exibicao.append("titular")
            if "motivo_descarte" in df_lixo.columns: cols_exibicao.append("motivo_descarte")
            elif "motivo" in df_lixo.columns: cols_exibicao.append("motivo")
            
            if cols_exibicao:
                st.dataframe(df_lixo[cols_exibicao], use_container_width=True)
            else:
                 st.write(descartados)
        else:
            st.info("A Lixeira está limpa.")
