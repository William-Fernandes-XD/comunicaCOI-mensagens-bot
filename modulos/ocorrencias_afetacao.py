from database_conexoes.Oper_DataGuard_connection import conectar
import schedule
import requests
import time
from utilitarios.variaveis_env import safe_env_get, safe_env_get_split
from time import sleep
from datetime import datetime, timedelta

def verificar_ocorrencias():
    connection = conectar()
    cursor = connection.cursor()

    # Consulta SQL para verificar pendências
    with open("sql/ocorrencias_afetacao.sql", "r") as file:
        query = file.read()

    cursor.execute(query)
    rows = cursor.fetchall()

    rows = [
        tuple(valor.read() if hasattr(valor, "read") else valor for valor in row)
        for row in rows
    ]

    cursor.close()
    connection.close()

    return rows

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
        data_inicio_oco, ocorrencia, regional, subestacao, alimentador_id, instalacao, clientes_pendentes = row

        ocorrencia = str(ocorrencia)

        ocorrencias_banco.add(ocorrencia)
        
        ## preparando o id do grupo
        id_whatsapp = safe_env_get("GRUPO_SOBREAVISO")
        mensagem = ""

        mensagem = (
                    f"🚨 *Comunicação de Ocorrências*\n\n"
                    f" *Ocorrência:* {ocorrencia}\n"
                    f" *Regional:* {regional}\n"
                    f" *Subestação:* {subestacao}\n"
                    f" *Alimentador:* {alimentador_id}\n"
                    f" *Instalação:* {instalacao}\n"
                    f" *Afetação:* {clientes_pendentes}\n"
                )

        ## Marcando o Ribas caso a afetação seja alta
        marcados_whatsapp = []
        
        if (clientes_pendentes >= 300):
            
            if clientes_pendentes >= 400:
                lideres = safe_env_get_split(safe_env_get("RIBAS_LIDER"))
                executivos = safe_env_get_split(safe_env_get("DERIVAN_EXECUTIVO"))
                gerentes = safe_env_get_split(safe_env_get("VINICYUS_GERENTE"))
                marcados_whatsapp = lideres + executivos + gerentes

            elif clientes_pendentes >= 350:
                lideres = safe_env_get_split(safe_env_get("RIBAS_LIDER"))
                executivos = safe_env_get_split(safe_env_get("DERIVAN_EXECUTIVO"))
                marcados_whatsapp = lideres + executivos

            elif clientes_pendentes >= 300:
                marcados_whatsapp = safe_env_get_split(safe_env_get("RIBAS_LIDER"))

            else:
                continue

            enviar_mensagem = false

            if ocorrencia in cache:
                 if datetime.now() - datetime.strptime(cache[idx]["ultima_atualizacao"], "%Y-%m-%d %H:%M:%S") >= timedelta(minutes=3):
                    #### FINALIZAR A PARTE DE CACHE DO ENVIO DE MENSAGENS
            else:
                cache[idx] = {
                    "ocorrencia": ocorrencia,
                    "regional": regional,
                    "subestacao": subestacao,
                    "alimentador": alimentador_id,
                    "afetacao": clientes_pendentes
                    "cache_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                enviar_mensagem = true
            try:
                payload = {
                    "chatId": id_whatsapp,
                    "message": mensagem,
                    "mentions": marcados_whatsapp if marcados_whatsapp else [],
                    "regional": regional
                }

                print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Ocorrência: {ocorrencia} | Regional: {regional} | Instalação: {instalacao}")


                res = requests.post(safe_env_get("WA_SERVER_URL"), json=payload, timeout=10)
            except Exception as e:
                print(f"Erro ao enviar mensagem para {regional} (Ocorrência {ocorrencia}): {e}")

            sleep(1) 


schedule.every(6).minutes.do(enviar_mensagem_ocorrencia_afetacao)

if __name__ == "__main__":
    enviar_mensagem_ocorrencia_afetacao()

    while True:
        schedule.run_pending()
        time.sleep(1)
