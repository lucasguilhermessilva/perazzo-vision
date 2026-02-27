from google import genai  # type: ignore
import os
import json
import time

print("🚀 Sistema Perazzinho - Módulo Caçador (Versão FEBRABAN com 1.5 Flash)!")

# Cole a sua chave Nível 1 aqui
CHAVE_API = "AIzaSyBw6mG79mmEjd9BT7MIf9Wub2FK6Y8vqbI"
client = genai.Client(api_key=CHAVE_API)

def cacar_no_processo(pasta_imagens):
    print(f"🔍 Vasculhando a pasta '{pasta_imagens}' em busca dos Saldos Anteriores...")
    
    arquivos = [f for f in os.listdir(pasta_imagens) if f.endswith('.png')]
    arquivos.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    
    extratos_encontrados = []
    
    # O PROMPT MÁGICO DO PERITO
    prompt_cacador = """
    Você é um perito contábil especialista em expurgos inflacionários (Planos Bresser, Verão, Collor I e II).
    Analise a imagem anexa. Se NÃO FOR um extrato de poupança, retorne APENAS: {"status": "lixo"}
    
    Se FOR um extrato, extraia OS DADOS EXATOS para preencher a calculadora do acordo FEBRABAN/STF.
    A calculadora exige o SALDO ANTERIOR (antes da aplicação dos rendimentos do mês).
    
    Retorne APENAS um JSON válido e puro neste formato:
    {
        "status": "sucesso",
        "titular": "nome do titular",
        "banco": "nome do banco",
        "conta": "numero da conta",
        "periodo": "periodo do extrato (ex: 18/12/90 a 17/01/91)",
        "saldo_base_calculo": "valor EXATO do SALDO ANTERIOR (ex: 940.089,47)"
    }
    """
    
    # Lendo o miolo onde deu erro antes (Páginas 15 a 30)
    for arquivo in arquivos[14:30]: 
        caminho = os.path.join(pasta_imagens, arquivo)
        print(f"👀 Analisando {arquivo}...")
        
        sucesso = False
        tentativas = 0
        
        # SISTEMA ANTI-CRASH E ANTI-BLOQUEIO
        while not sucesso and tentativas < 3:
            try:
                imagem_ia = client.files.upload(file=caminho)
                
                # Usando o 1.5 Flash (O trator de OCR com limites muito maiores)
                resposta = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=[prompt_cacador, imagem_ia]
                )
                
                if not resposta.text:
                    raise ValueError("Resposta da IA veio vazia.")

                texto_limpo = resposta.text.replace('```json', '').replace('```', '').strip()
                dados = json.loads(texto_limpo)
                
                if dados.get("status") == "sucesso":
                    print(f"   🎯 BINGO! Dados FEBRABAN extraídos da {arquivo}.")
                    dados["pagina"] = arquivo
                    extratos_encontrados.append(dados)
                else:
                    print(f"   🗑️ Lixo descartado ({arquivo}).")
                
                # Apaga o arquivo do servidor do Google para manter sigilo
                client.files.delete(name=imagem_ia.name)
                sucesso = True 
                
                time.sleep(5) # Pausa leve maior para estabilizar a API
                
            except Exception as e:
                tentativas += 1
                erro_str = str(e)
                if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                    print(f"   ⚠️ Rate Limit! Respirando por 30 segundos... (Tentativa {tentativas}/3)")
                    time.sleep(30)
                else:
                    print(f"   ⚠️ Falha na matrix ({e}). Retentando... (Tentativa {tentativas}/3)")
                    time.sleep(3)

    print("\n" + "="*50)
    print("🏆 RESULTADO FINAL (Pronto para a Calculadora):")
    print(json.dumps(extratos_encontrados, indent=4, ensure_ascii=False))
    print("="*50)

pasta = "imagens_extratos"
if os.path.exists(pasta):
    cacar_no_processo(pasta)
else:
    print("❌ Pasta não encontrada.")