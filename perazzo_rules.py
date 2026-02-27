import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class FiltroJuridico:
    """Motor de Regras Jurídicas e Financeiras para Expurgos (Acordo FEBRABAN)"""
    
    @staticmethod
    def validar_aniversario(data_aniversario_str: str) -> bool:
        """
        Regra FEBRABAN: Planos Bresser (1987) e Verão (1989) exigem que a conta tenha
        recebido rendimentos entre o dia 01 e 15. Contas que fazem aniversário na
        segunda quinzena (16 a 31) não têm direito ao expurgo.
        """
        try:
            dia = int(str(data_aniversario_str).strip())
            return 1 <= dia <= 15
        except (ValueError, TypeError):
            # Se não conseguir identificar o dia, enviamos para análise manual (não descarta cego)
            logger.warning(f"⚠️ Dia de aniversário não numérico detectado: {data_aniversario_str}")
            return True 

    @staticmethod
    def banir_collor_i(periodo_str: str) -> bool:
        """
        O escritório não atua no Plano Collor I. Excluímos extratos
        que correspondam com meses chave de 1990 (especialmente março a maio).
        Se a data for ambígua, mantemos para análise.
        """
        if not periodo_str:
            return False # Mantém na dúvida
            
        periodo = periodo_str.lower()
        
        # Palavras-chave ou indícios de 1990
        # Ex: "01/03/90 a 01/04/90" ou "ABR/1990"
        tem_1990 = "1990" in periodo or "/90" in periodo or "-90" in periodo
        
        return tem_1990

    @staticmethod
    def ajustar_moeda_cruzados(saldo: float, periodo_str: str) -> float:
        """
        Regra de Moeda: Em meados de Janeiro de 1989 houve a conversão de
        Cruzados (Cz$) para Cruzados Novos (NCz$).
        Se o sistema identificar que o extrato é do Bresser (1987) ou 
        início do Verão em Cruzados velhos, divide por 1000.
        Cruzados para Cruzados Novos = / 1000.
        """
        if not periodo_str:
            return saldo
            
        periodo = periodo_str.lower()
        
        # Se for 1987 (Bresser) ou 1988 é definitivamente Cruzado (Cz$)
        is_cruzado_velho = any(ano in periodo for ano in ["1987", "/87", "-87", "1988", "/88", "-88"])
        
        # O Plano Verão ocorreu na transição (Jan/1989). É perigoso cortar
        # zeros se o banco já emitiu em NCz$ (Cruzados Novos).
        # Para Fevereiro/1989 em diante, NUNCA corta 3 zeros (Já é NCz$)
        # Para Plano Collor II (1991), é Cruzeiro (Cr$), NUNCA corta.
        
        if is_cruzado_velho:
            logger.info(f"🔄 Ajuste Monetário (Cz$ -> NCz$): Cortando 3 zeros. Original: {saldo}")
            return saldo / 1000.0
            
        return saldo

    @classmethod
    def processar_lote_extratos(cls, lista_json_gemini: List[Dict]) -> Dict[str, Dict]:
        """
        Aplica as regras jurídicas na salada de extratos devolvidos pela IA.
        Garante o Retorno Único por conta (o extrato de maior valor que for elegível).
        """
        contas_processadas = {} # Formato: { "numero_conta": dict_do_melhor_extrato }
        descartados = []
        
        for extrato in lista_json_gemini:
            # Pula os que o Gemini já identificou como lixo na etapa de OCR
            if extrato.get("status") == "lixo":
                extrato["motivo_descarte"] = "Recusado pelo Perito de IA (Não é extrato)"
                descartados.append(extrato)
                continue
                
            conta_num = extrato.get("conta", "CONTA_DESCONHECIDA")
            periodo = str(extrato.get("periodo_extrato", ""))
            dia_aniv = extrato.get("data_aniversario", "")
            
            # --- Aplicação dos Filtros Francos-Atiradores ---
            
            # 1. Banimento Collor I (1990)
            if cls.banir_collor_i(periodo):
                extrato["status"] = "lixo"
                extrato["motivo_descarte"] = "Plano Collor I detectado (1990) - Fora do Escopo"
                descartados.append(extrato)
                continue
                
            # 2. Dia de Aniversário Elegível (Dia 01 a 15)
            if not cls.validar_aniversario(dia_aniv):
                extrato["status"] = "lixo"
                extrato["motivo_descarte"] = f"Aniversário Fora do Período Elegível (Dia: {dia_aniv}). Exigido: 01-15"
                descartados.append(extrato)
                continue
                
            # Tratamento de Saldo numérico
            try:
                # Transforma string em float se bobear, embora o prompt exija numérico
                saldo_cru = float(extrato.get("saldo_anterior_base", 0))
            except ValueError:
                extrato["status"] = "erro"
                extrato["motivo_descarte"] = f"Falha ao ler saldo: {extrato.get('saldo_anterior_base')}"
                descartados.append(extrato)
                continue
                
            # 3. Ajuste Monetário da Inflação (O Retorno do Jedi)
            saldo_corrigido = cls.ajustar_moeda_cruzados(saldo_cru, periodo)
            extrato["saldo_anterior_base_ajustado"] = round(saldo_corrigido, 2)
            
            # 4. A Batalha pelo Maior Saldo Único (Portal FEBRABAN)
            if conta_num not in contas_processadas:
                contas_processadas[conta_num] = extrato
            else:
                saldo_antigo_campeao = contas_processadas[conta_num]["saldo_anterior_base_ajustado"]
                saldo_novo_desafiante = extrato["saldo_anterior_base_ajustado"]
                
                if saldo_novo_desafiante > saldo_antigo_campeao:
                    # O novo destrona o velho
                    perdedor = contas_processadas[conta_num].copy()
                    perdedor["status"] = "lixo"
                    perdedor["motivo_descarte"] = f"Perdeu a Batalha de Saldo para outro extrato na mesma conta (Novo Maior: {saldo_novo_desafiante})"
                    descartados.append(perdedor)
                    
                    contas_processadas[conta_num] = extrato
                else:
                    # O novo entra pro lixo
                    extrato["status"] = "lixo"
                    extrato["motivo_descarte"] = f"Menor Saldo na Conta (Mantido Maior: {saldo_antigo_campeao})"
                    descartados.append(extrato)
                    
        return {
            "elegiveis": list(contas_processadas.values()),
            "descartados": descartados
        }

# Função apenas para testar isolado no console se batermos 'python perazzo_rules.py'
if __name__ == "__main__":
    extratos_fake = [
         {"status": "sucesso", "conta": "12345-6", "periodo_extrato": "JUN/87", "data_aniversario": "10", "saldo_anterior_base": 1500000},
         {"status": "sucesso", "conta": "12345-6", "periodo_extrato": "MAI/87", "data_aniversario": "10", "saldo_anterior_base": 800000},
         {"status": "sucesso", "conta": "99999-9", "periodo_extrato": "JAN/89", "data_aniversario": "22", "saldo_anterior_base": 5000}, # Aniv furado
         {"status": "sucesso", "conta": "66666-6", "periodo_extrato": "MAR/1990", "data_aniversario": "01", "saldo_anterior_base": 120000}, # Collor I
    ]
    
    print("Testando Motor de Regras...")
    resultado = FiltroJuridico.processar_lote_extratos(extratos_fake)
    
    print("\nELEGÍVEIS (Vão pro Acordo):")
    for r in resultado["elegiveis"]:
        print(f"> Conta {r['conta']} | Saldo Ajustado: {r['saldo_anterior_base_ajustado']}")
        
    print("\nDESCARTADOS:")
    for d in resultado["descartados"]:
        print(f"> Conta {d.get('conta', 'N/A')} | Motivo: {d['motivo_descarte']}")
