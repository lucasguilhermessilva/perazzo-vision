import streamlit as st
from google import genai
import os
import json
import time

# Configuração da página - A cara do Perazzo Vision
st.set_page_config(page_title="Perazzo Vision | Expurgos", page_icon="👁️", layout="wide")

CHAVE_API = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=CHAVE_API)

# Interface Gráfica
st.title("👁️ Perazzo Vision")
st.subheader("Módulo de Inteligência: Mineração de Expurgos FEBRABAN")
st.markdown("---")

pasta_imagens = "imagens_extratos"

if st.button("🚀 Iniciar Varredura de Extratos", type="primary"):
    if not os.path.exists(pasta_imagens):
        st.error("❌ A pasta 'imagens_extratos' não foi encontrada. Rode o extrator de PDF primeiro.")
    else:
        arquivos = [f for f in os.listdir(pasta_imagens) if f.endswith('.png')]
        arquivos.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
        
        st.info(f"📊 Encontradas {len(arquivos)} imagens. Iniciando motor de IA...")
        
        # Barra de progresso bonitona
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        extratos_encontrados = []
        
        prompt_cacador = """
        Você é um perito contábil. Se a imagem NÃO for um extrato de poupança, retorne APENAS: {"status": "lixo"}
        Se FOR um extrato, extraia o SALDO ANTERIOR (antes dos rendimentos do mês).
        Retorne APENAS um JSON:
        { "status": "sucesso", "titular": "nome", "banco": "banco", "conta": "numero", "periodo": "periodo", "saldo_base_calculo": "valor" }
        """
        
        # Lendo um lote de teste (Páginas 14 a 30)
        lote_arquivos = arquivos[14:30]
        total_arquivos = len(lote_arquivos)
        
        for i, arquivo in enumerate(lote_arquivos):
            caminho = os.path.join(pasta_imagens, arquivo)
            status_text.text(f"👀 O Perazzo Vision está analisando a {arquivo}...")
            
            sucesso = False
            tentativas = 0
            
            while not sucesso and tentativas < 3:
                try:
                    imagem_ia = client.files.upload(file=caminho)
                    resposta = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[prompt_cacador, imagem_ia]
                    )
                    
                    if resposta.text:
                        texto_limpo = resposta.text.replace('```json', '').replace('```', '').strip()
                        dados = json.loads(texto_limpo)
                        
                        if dados.get("status") == "sucesso":
                            dados["pagina"] = arquivo
                            extratos_encontrados.append(dados)
                            st.toast(f"🎯 BINGO! Extrato achado na {arquivo}!") # Notificação popup
                            
                    client.files.delete(name=imagem_ia.name)
                    sucesso = True
                    time.sleep(2)
                    
                except Exception as e:
                    tentativas += 1
                    time.sleep(3)
            
            # Atualiza a barra de progresso
            progress_bar.progress((i + 1) / total_arquivos)
            
        status_text.text("✅ Varredura concluída com sucesso!")
        st.markdown("---")
        
        # Mostrando os resultados em uma tabela profissional
        if extratos_encontrados:
            st.success("🏆 Resultados extraídos e prontos para a FEBRABAN:")
            st.dataframe(extratos_encontrados, use_container_width=True)
        else:
            st.warning("Nenhum extrato válido foi encontrado neste lote.")