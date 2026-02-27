import fitz  # PyMuPDF
import os

def fatiar_pdf_para_imagens(caminho_pdf, pasta_saida, dpi=300):
    print(f"🚀 Iniciando o Perazzinho Vision - Fatiando: {caminho_pdf}")
    
    # cria a pasta de saída se não existir
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)
        
    try:
        doc = fitz.open(caminho_pdf)
    except Exception as e:
        print(f"❌ Erro ao abrir o PDF: {e}")
        return
        
    # varrer o PDF página por página
    for num_pagina in range(len(doc)):
        pagina = doc.load_page(num_pagina)
        
        # aumentando a resolução (DPI) para a IA ler os números antigos perfeitamente
        zoom = dpi / 72 
        matriz = fitz.Matrix(zoom, zoom)
        
        # transforma a página em imagem
        pix = pagina.get_pixmap(matrix=matriz, alpha=False)
        
        caminho_imagem = os.path.join(pasta_saida, f"pagina_{num_pagina + 1}.png")
        pix.save(caminho_imagem)
        print(f"✅ Página {num_pagina + 1} convertida com sucesso.")

    print("🏁 Extração concluída. As imagens estão prontas para o Cérebro da IA.")

# testar pdf
pdf_teste = "processo_gigante.pdf" 
fatiar_pdf_para_imagens(pdf_teste, "imagens_extratos")