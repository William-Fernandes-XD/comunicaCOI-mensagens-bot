from database_conexoes.Oper_DataGuard_connection import conectar
import requests
import time
from utilitarios.variaveis_env import safe_env_get, safe_env_get_split
from time import sleep
from datetime import datetime, timedelta
import os 
import json

def verificar_ocorrencias():
    connection = conectar()

    try:
        with connection.cursor() as cursor:
            with open("sql/ocorrencias_afetacao.sql", "r", encoding="utf-8") as file:
                query = file.read()

            cursor.execute(query)
            rows = cursor.fetchall()

            rows = [
                tuple(
                    valor.read() if hasattr(valor, "read") else valor
                    for valor in row
                )
                for row in rows
            ]

            return rows

    finally:
        connection.close()

def enviar_mensagem_ocorrencia_afetacao():
    
    ocorrencias = verificar_ocorrencias()

    ## verificando cache de ocorrencias já enviadas
    arquivo_cache = "cache_enviado/ocorrencias_afetacao.json"

    ## garantindo que existe a pasta cache_enviado
    os.makedirs("cache_enviado", exist_ok=True)

    ## verificando se o arquivo de cache existe e carregando-o
    if(os.path.exists(arquivo_cache)):
        with open(arquivo_cache, "r", encoding="utf-8") as arquivo:
            try:
                cache = json.load(arquivo)
            except json.JSONDecodeError:
                print("Erro ao decodificar o arquivo de cache. O arquivo pode estar corrompido.")
                cache = {}
    else:
        cache = {}

    ## ocorrencias vindas do banco
    ocorrencias_banco = set()

    for row in ocorrencias:
        data_inicio_oco, ocorrencia, regional, subestacao, alimentador_id, instalacao, clientes_pendentes, motivo_reclamacao, status, data_ultimo_evento = row

        ocorrencia = str(ocorrencia)

        ocorrencias_banco.add(ocorrencia)
        
        ## preparando o id do grupo
        id_whatsapp = safe_env_get("GRUPO_SOBREAVISO")

        data_inicio = datetime.strptime(data_inicio_oco, "%d/%m/%Y %H:%M:%S")

        mensagem = (
            f"🚨 *Comunicação de Ocorrências*\n\n"
            f"*Início da Ocorrência:* {data_inicio.strftime('%d/%m/%Y %H:%M')}\n"
            f"*Ocorrência:* {ocorrencia}\n"
            f"*Afetação:* {clientes_pendentes}\n"
            f"*Status:* {status}\n"
            f"*Motivo:* {motivo_reclamacao}\n"
            f"*Regional:* {regional}\n"
            f"*Subestação:* {subestacao}\n"
            f"*Alimentador:* {alimentador_id}\n"
            f"*Instalação:* {instalacao}"
        )

        ## Marcando o Ribas caso a afetação seja alta
        marcados_whatsapp = []
        
        if (clientes_pendentes >= 400):
            
            if clientes_pendentes >= 1500:
                lideres = safe_env_get_split(safe_env_get("RIBAS_LIDER"))
                executivos = safe_env_get_split(safe_env_get("DERIVAN_EXECUTIVO"))
                gerentes = safe_env_get_split(safe_env_get("VINICYUS_GERENTE"))
                marcados_whatsapp = lideres + executivos + gerentes

            elif clientes_pendentes >= 1000:
                lideres = safe_env_get_split(safe_env_get("RIBAS_LIDER"))
                executivos = safe_env_get_split(safe_env_get("DERIVAN_EXECUTIVO"))
                marcados_whatsapp = lideres + executivos

            elif clientes_pendentes >= 400:
                marcados_whatsapp = safe_env_get_split(safe_env_get("RIBAS_LIDER"))

            else:
                continue

            enviar_mensagem = False

            ## Verifica se o ultimo evento do banco tem mais de 10 minutos
            ## Validando se nosso dado vindo do banco já existe
            ## Caso exista, então faça uma verficação se a afetação variou
            ## Se variar, reenvie. Caso contrário, não envie


            data_ultimo_evento_to_date = datetime.strptime(data_ultimo_evento, "%d/%m/%Y %H:%M:%S")
            print(data_ultimo_evento_to_date)

            if ((datetime.now() - data_ultimo_evento_to_date) > timedelta(minutes=10)):
                if ocorrencia in cache:
                    cache[ocorrencia]["afetacao"] = clientes_pendentes
                    if (clientes_pendentes > cache[ocorrencia]["afetacao"]):
                        enviar_mensagem = True
                        cache[ocorrencia]["ultima_atualizacao"] = (datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    cache[ocorrencia] = {
                        "ocorrencia": ocorrencia,
                        "regional": regional,
                        "subestacao": subestacao,
                        "alimentador": alimentador_id,
                        "afetacao": clientes_pendentes,
                        "cache_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    enviar_mensagem = True

            if enviar_mensagem:
                try:
                    payload = {
                        "chatId": id_whatsapp,
                        "message": mensagem,
                        "mentions": marcados_whatsapp if marcados_whatsapp else [],
                        "regional": regional
                    }

                    print(f"✅ [{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Ocorrência: {ocorrencia} | Regional: {regional} | Instalação: {instalacao}")
                    
                    res = requests.post(safe_env_get("WA_SERVER_URL"), json=payload, timeout=10)

                except Exception as e:
                    print(f"Erro ao enviar mensagem para {regional} (Ocorrência {ocorrencia}): {e}")

                sleep(1) 

    ## removendo ocorrencias que não estão mais no banco de dados, para manter limpo
    cache = {
        ocorrencia: dados
        for ocorrencia, dados in cache.items()
        if ocorrencia in ocorrencias_banco
    }

    # Salva o cache atualizado
    with open(arquivo_cache, "w", encoding="utf-8") as arquivo:
        json.dump(cache, arquivo, ensure_ascii=False, indent=4)
