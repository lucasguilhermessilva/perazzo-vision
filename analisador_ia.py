from google import genai
import os
import json

print("🚀 Sistema Perazzinho Iniciado! Carregando os módulos...")

# 1. Configuração da sua chave de API
CHAVE_API = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=CHAVE_API)

def analisar_extrato(caminho_imagem):
    print(f"🧠 Enviando a imagem '{caminho_imagem}' para a Inteligência Artificial ler...")
    
    prompt = """
    Você é um advogado especialista em Direito Bancário e expurgos inflacionários (Planos Bresser, Verão, Collor).
    Analise esta imagem de um processo judicial. Ela pode ser um extrato bancário ou uma petição.
    Se for um extrato, extraia as informações e retorne APENAS um JSON válido, sem formatação markdown extra:
    {
        "titular": "nome completo do titular da conta",
        "banco": "nome do banco (ex: Bradesco, Bandepe, Econômico)",
        "conta": "número da conta",
        "saldo_base": "saldo principal ou último saldo do período em formato string"
    }
    Se a imagem não contiver dados de extrato de poupança/conta, retorne EXATAMENTE este JSON:
    {"erro": "Não é um extrato válido"}
    """
    
    try:
        # Fazer o upload do arquivo para a IA usando o novo formato
        imagem_ia = client.files.upload(file=caminho_imagem)
        
        # Gerar o conteúdo usando o modelo atualizado
        resposta = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, imagem_ia]
        )
        
        texto_limpo = resposta.text.replace('```json', '').replace('```', '').strip()
        dados = json.loads(texto_limpo)
        
        if "erro" in dados:
            print("🗑️ Página descartada (Não é extrato).")
        else:
            print("💎 Sucesso! Ouro extraído:")
            print(json.dumps(dados, indent=4, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Falha na conexão com a IA: {e}")

# Verificando as imagens
pasta = "imagens_extratos"
print(f"🔍 Procurando a pasta '{pasta}'...")

if not os.path.exists(pasta):
    print(f"❌ A pasta '{pasta}' não foi encontrada no diretório atual.")
else:
    print(f"✅ Pasta '{pasta}' encontrada! Procurando os extratos...")
    # Testando apenas a primeira página
    imagem_teste = os.path.join(pasta, "pagina_1.png")
    
    if os.path.exists(imagem_teste):
        analisar_extrato(imagem_teste)
    else:
        print(f"❌ O arquivo '{imagem_teste}' não foi encontrado dentro da pasta.")

print("🏁 Fim do script.")