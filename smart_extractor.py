import asyncio
import json
import os
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from google import genai
from typing import List, Dict

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RateLimitException(Exception):
    pass

class SmartExtractor:
    def __init__(self, api_key: str = None):
        self.api_key = None
        try:
            import streamlit as st
            # Tenta buscar do st.secrets primeiro (Nuvem)
            if "GEMINI_API_KEY" in st.secrets:
                self.api_key = st.secrets["GEMINI_API_KEY"]
            else:
                self.api_key = None
        except Exception:
            self.api_key = None
            
        if not self.api_key:
            # Fallback para Variaveis de Ambiente. Se NÃO ESTIVER, não usamos hardcoded de produção.
            self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not self.api_key:
                 raise ValueError("⚠️ [SEGURANÇA] Nenhuma API Key do Gemini configurada. Use Streamlit Secrets ou Variavel de Ambiente 'GEMINI_API_KEY'.")
            
        # Inicia o client oficial com a chave
        self.client = genai.Client(api_key=self.api_key)
        
    def gerar_prompt_atirador(self, nome_alvo: str) -> str:
        return f"""
        Você é um perito contábil investigando expurgos inflacionários (Planos Bresser, Verão, Collor I e II).
        
        Sua missão é EXTREMAMENTE focada. O NOSSO CLIENTE É: "{nome_alvo}".
        
        Analise a imagem da página anexa. 
        REGRA 1: Se NÃO FOR um documento de banco/extrato (se for rg, petição, ou conta de luz), retorne APENAS: {{"status": "lixo", "motivo": "Não é extrato"}}
        REGRA 2: Se FOR um extrato, identifique o TITULAR. Se o titular NÃO bater com "{nome_alvo}" (lembrando que os bancos abreviam nomes ex: AMARO A. SILVA), você DEVE descarta-lo. Retorne APENAS: {{"status": "lixo_terceiro", "motivo": "Extrato de Terceiro (titular na conta é diferente do alvo)"}}
        
        Se FOR um extrato E pertencer ao "{nome_alvo}", extraia OS DADOS EXATOS.
        
        Retorne APENAS um JSON válido e puro neste formato (sem markdown varrendo saldo_anterior_base como numero):
        {{
            "status": "sucesso",
            "titular": "NOME LIDO NA IMAGEM",
            "banco": "NOME DO BANCO",
            "conta": "NUMERO DA CONTA (COM DIGITO)",
            "periodo_extrato": "PERIODO DO EXTRATO (ex: 18/12/90 a 17/01/91)",
            "data_aniversario": "DIA DO ANIVERSÁRIO DA CONTA (ex: 17)",
            "saldo_anterior_base": "VALOR NUMÉRICO DO SALDO ANTERIOR EXATO (ex: 940089.47)"
        }}
        """

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=60), # Espera 4s, 8s, 16s... até 60s
        stop=stop_after_attempt(10), # Desiste após 10 tentativas
        retry=retry_if_exception_type((RateLimitException)), # Só faz retry se for problema de limitação de cota
        before_sleep=lambda retry_state: logger.warning(f"⚠️ [Rate Limit] Respirando... Tentativa {retry_state.attempt_number}/10. Detalhes: {retry_state.outcome.exception()}")
    )
    async def processar_imagem_com_retry(self, imagem_path: str, nome_alvo: str) -> dict:
        """
        Pega UMA imagem, faz o upload, analisa e deleta. Se tomar Rate Limit (429), pausa e tenta de novo automaticamente.
        """
        logger.info(f"🔍 Enviando para o Gemini: {os.path.basename(imagem_path)} (Alvo: {nome_alvo})")
        
        file_upload = None
        try:
            # Envio Assíncrono para o servidor (Google GenAI)
            file_upload = await asyncio.to_thread(self.client.files.upload, file=imagem_path)
            
            prompt_montado = self.gerar_prompt_atirador(nome_alvo)
            
            resposta = await self.client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt_montado, file_upload],
                config={"temperature": 0.1} # Baixa temperatura = maior aderência ao JSON
            )
            
            if not resposta.text:
                raise ValueError("Resposta vazia da API.")
                
            texto_limpo = resposta.text.replace('```json', '').replace('```', '').strip()
            dados = json.loads(texto_limpo)
            
            logger.info(f"✅ Sucesso em {os.path.basename(imagem_path)}! Status: {dados.get('status')}")
            return dados
            
        except Exception as e:
            msg_erro = str(e).lower()
            if "429" in msg_erro or "exhausted" in msg_erro or "quota" in msg_erro:
                raise RateLimitException(f"Cota estourada ({e})")
            else:
                logger.error(f"❌ Erro Irreversível em {imagem_path}: {e}")
                return {"status": "erro", "erro": str(e)}
                
        finally:
            # Segurança e Sigilo: Deleta imagem do servidor do AI Studio
            if file_upload:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=file_upload.name)
                except Exception as del_err:
                    logger.error(f"⚠️ Erro ao deletar arquivo {file_upload.name}: {del_err}")

    async def extrair_lote(self, lista_imagens: List[str], max_concorrencia: int = 5, nome_alvo: str = "") -> List[Dict]:
        """
        Gerencia o gargalo. Processa uma lista gigante de imagens, mas não dispara tudo de vez.
        Usa um Semaphore para limitar N chamadas simultâneas.
        """
        semaphore = asyncio.Semaphore(max_concorrencia)
        
        async def processar_com_semaforo(img):
            async with semaphore:
                resultado = await self.processar_imagem_com_retry(img, nome_alvo)
                resultado["arquivo_origem"] = os.path.basename(img)
                return resultado
                
        logger.info(f"🚀 Iniciando processamento em lote de {len(lista_imagens)} fragmentos...")
        tarefas = [processar_com_semaforo(img) for img in lista_imagens]
        
        # Dispara as tarefas de forma concorrente e espera todas terminarem
        resultados = await asyncio.gather(*tarefas)
        
        logger.info("🏁 Lote finalizado!")
        return resultados

# === TRECHO PARA TESTE LOCAL ===
if __name__ == "__main__":
    import glob
    
    async def teste_rapido():
        extractor = SmartExtractor()
        # Pega as primeiras 3 imagens da sua pasta de testes
        imagens = glob.glob("imagens_extratos/*.png")[:3]
        if imagens:
            resultados = await extractor.extrair_lote(imagens, max_concorrencia=2)
            print(json.dumps(resultados, indent=4, ensure_ascii=False))
        else:
            print("Nenhuma imagem PNG encontrada em 'imagens_extratos/' para teste.")
            
    # asyncio.run(teste_rapido())
