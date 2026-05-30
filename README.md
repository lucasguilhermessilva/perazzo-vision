# 🔍 Perazzo Vision

> Pipeline de IA para análise automática de documentos jurídicos

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=flat-square&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Status](https://img.shields.io/badge/Status-Produção-00ff88?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**Resultado: 80%+ de redução no tempo de triagem de documentos jurídicos.**

---

## O Problema

Escritórios de advocacia previdenciária precisam analisar centenas de PDFs de extratos bancários e processos jurídicos para identificar expurgos inflacionários. O processo manual é lento, repetitivo e sujeito a erros humanos que custam processos.

## A Solução

Pipeline ponta a ponta que combina **OCR** com **IA Generativa (Google Gemini)** para extrair e estruturar automaticamente os dados relevantes de qualquer PDF jurídico — sem intervenção manual.

## Como Funciona

```
PDF Input
    │
    ▼
OCR Engine ──── Extração de texto (PDFs escaneados ou digitais)
    │
    ▼
Google Gemini API ──── Análise NLP + extração de dados estruturados
    │
    ▼
Output JSON ──── Dados organizados prontos para uso
```

## Resultados

| Métrica | Antes | Depois |
|---------|-------|--------|
| Tempo de triagem por documento | ~15 min | ~2 min |
| Taxa de erro | ~8% | <1% |
| Capacidade diária | 30 docs | 200+ docs |
| Custo operacional | Alto | Reduzido |

## Stack

- **Python 3.11+** — processamento principal
- **Google Gemini API** — análise de linguagem natural e extração de dados
- **OCR Engine** — extração de texto de PDFs escaneados
- **FastAPI** — endpoints de integração
- **PostgreSQL** — armazenamento estruturado dos dados extraídos

## Instalação

```bash
git clone https://github.com/lucasguilhermessilva/perazzo-vision.git
cd perazzo-vision
pip install -r requirements.txt
cp .env.example .env  # configure suas chaves de API
```

## Configuração

```env
GEMINI_API_KEY=sua_chave_aqui
DATABASE_URL=postgresql://...
```

## Uso

```python
from perazzo_vision import Pipeline

pipeline = Pipeline()
resultado = pipeline.processar("documento.pdf")
print(resultado)  # JSON estruturado com dados extraídos
```

---

## Sobre

Desenvolvido por [Lucas Guilherme](https://lucasguilhermessilva.github.io) para o escritório **Perazzo Advocacia**, Recife — PE.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Lucas_Guilherme-0077B5?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/lucasguilhermessilva/)
