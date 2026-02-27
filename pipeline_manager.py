import os
import shutil
import fitz  # PyMuPDF
import pandas as pd
import logging
from typing import List, Tuple
from smart_extractor import SmartExtractor
from perazzo_rules import FiltroJuridico
import asyncio

logger = logging.getLogger(__name__)

class PipelineManager:
    def __init__(self, dir_pje: str = "dados/entrada_pje", dir_frag: str = "dados/fragmentos"):
        self.dir_pje = dir_pje
        self.dir_frag = dir_frag
        self.extractor = SmartExtractor()
        
        # Garante que as pastas base existem
        os.makedirs(self.dir_pje, exist_ok=True)
        os.makedirs(self.dir_frag, exist_ok=True)

    def preparar_area_trabalho(self, nome_processo: str) -> str:
        """Limpa e cria uma pasta de fragmentos exclusiva para o processo atual"""
        pasta_processo = os.path.join(self.dir_frag, nome_processo)
        if os.path.exists(pasta_processo):
            shutil.rmtree(pasta_processo)
        os.makedirs(pasta_processo)
        return pasta_processo

    def is_lixo_heuristico(self, text: str) -> bool:
        """
        Pré-Filtro Local (O Herói da Economia de Tokens):
        A maioria dos PDFs do PJe são petições e sentenças (muito texto) misturados com 
        extratos (tabelas e números difusos escaneados).
        Se a página tiver uma quantidade excessiva de caracteres limpos reconhecíveis 
        por OCR básico, provavelmente é texto corrido (petição/juntada) e NÃO um extrato escaneado.
        """
        if not text: 
            return False # Se vier vazio do OCR basico, pode ser imagem pura. Envia pro Gemini.
            
        tamanho = len(text.strip())
        texto_lower = text.lower()
        
        # Palavras denunciantes de lixo jurídico
        if any(palavra in texto_lower for palavra in ["procuração", "petição inicial", "contestação", "cópia reprográfica"]):
             return True
             
        # Lógica de densidade de texto: Extratos são tabulares ("DATA", "HISTORICO", "SALDO")
        # Textos com mais de 1000 caracteres de texto legível de máquina geralmente são docs, não imagens 
        # rústicas de microfilmagens.
        if tamanho > 1500:
            return True
            
        return False

    def fatiar_pdf_pje(self, caminho_pdf: str, pasta_saida: str) -> List[str]:
        """
        Pega um PDF monstro do PJe, divide em páginas soltas (.png) e 
        já descarta as páginas que CLARAMENTE são petições, usando fitz.
        """
        logger.info(f"🔪 Fatiando o monstro: {os.path.basename(caminho_pdf)}")
        imagens_validas = []
        doc = fitz.open(caminho_pdf)
        
        for num_pag in range(len(doc)):
            pagina = doc.load_page(num_pag)
            
            # Tenta extrair texto da camada do PDF primeiro
            texto_cru = pagina.get_text()
            
            if self.is_lixo_heuristico(texto_cru):
                logger.debug(f"🗑️ Pré-filtro descartou Página {num_pag+1} (Muito texto, provavelmente petição)")
                continue
                
            # Se passou no pré-filtro, renderiza como imagem para o Gemini OCR
            pix = pagina.get_pixmap(matrix=fitz.Matrix(2, 2)) # DPI razoável para o Gemini não embaçar
            nome_arq = f"pag_{num_pag+1:04d}.png"
            caminho_img = os.path.join(pasta_saida, nome_arq)
            pix.save(caminho_img)
            imagens_validas.append(caminho_img)
            
        doc.close()
        logger.info(f"✅ Fatiamento concluído. {len(imagens_validas)} páginas sobreviveram ao pré-filtro de {len(doc)} totais.")
        return imagens_validas

    async def rodar_processo_unico(self, caminho_pdf: str, nome_alvo: str) -> dict:
        """Processa um PDF específico enviado pela interface UI focando no Cliente Alvo."""
        relatorio_geral = {"elegiveis": [], "descartados": [], "dossie_path": None}
        
        if not os.path.exists(caminho_pdf):
            logger.warning(f" Arquivo não encontrado: {caminho_pdf}")
            return relatorio_geral
            
        nome_proc = os.path.basename(caminho_pdf).replace(".pdf", "")
        pasta_trabalho = self.preparar_area_trabalho(nome_proc)
        
        # 1. Fatia e filtra localmente
        fragmentos = self.fatiar_pdf_pje(caminho_pdf, pasta_trabalho)
        
        if not fragmentos:
            logger.info(f"Processo {nome_proc} vazio de imagens úteis.")
            return relatorio_geral
            
        # 2. IA Extratora Sabe o Nome do Alvo
        # Usamos concurrent para o Gemini (limitando acesso max)
        lista_jsons_crus = await self.extractor.extrair_lote(fragmentos, max_concorrencia=3, nome_alvo=nome_alvo)
        
        # 3. O Juiz
        resultado_juridico = FiltroJuridico.processar_lote_extratos(lista_jsons_crus)
        
        relatorio_geral["elegiveis"].extend(resultado_juridico["elegiveis"])
        relatorio_geral["descartados"].extend(resultado_juridico["descartados"])
        
        # 4. GERAÇÃO DO DOSSIÊ OFICIAL DO CLIENTE (O PDF BAIXÁVEL)
        if resultado_juridico["elegiveis"]:
            caminho_outputs = "dados/outputs"
            os.makedirs(caminho_outputs, exist_ok=True)
            dossie_path = os.path.join(caminho_outputs, f"Dossie_Expurgos_{nome_alvo.replace(' ', '_')}_{nome_proc}.pdf")
            
            # Monta um PDF novo apenas com as fotos de extratos que ganharam
            doc_dossie = fitz.open()
            streams_abertos = []
            
            for e in resultado_juridico["elegiveis"]:
                # Recupera o caminho da imagem original a partir do resultado JSON
                arq_origem = e.get("arquivo_origem")
                if arq_origem:
                    img_path = os.path.join(pasta_trabalho, arq_origem)
                    if os.path.exists(img_path):
                        # Solução para "Document Closed" do PyMuPDF:
                        # 1. Abre a imagem original
                        img_doc = fitz.open(img_path)
                        # 2. Converte pra bytes de PDF
                        pdf_bytes = img_doc.convert_to_pdf()
                        img_doc.close() # O documento da imagem já fez o trabalho dele
                        
                        # 3. Abre como um stream na memória
                        pdf_temporario = fitz.open("pdf", pdf_bytes)
                        
                        # Guardamos a referência na lista antes de passar pro mestre
                        streams_abertos.append(pdf_temporario)
                        
                        # 4. Copia explicitamente a página para o documento mestre
                        doc_dossie.insert_pdf(pdf_temporario)
            
            doc_dossie.save(dossie_path)
            doc_dossie.close()
            
            # 5. Fecha todos os streams isolados só APÓS salvar a Master Piece.
            for s in streams_abertos:
                s.close()
                
            relatorio_geral["dossie_path"] = dossie_path
            logger.info(f"📚 Dossiê compilado com sucesso em: {dossie_path}")
                
        return relatorio_geral

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = PipelineManager()
    
    # Criar pastas para que o usuário jogue os PDFs dentro depois
    print(f"Pastas operacionais criadas em {pipeline.dir_pje}")
