from database_conexoes.comunicaCOI_database_connection import conectar
import schedule
from datetime import datetime, timedelta
import requests
import json
import os
import time
from utilitarios.variaveis_env import safe_env_get, safe_env_get_split
from time import sleep

# =========================
# MAPA DE GRUPOS
# =========================

MAPA_REGIONAIS = {
    "Goiânia": "GRUPO_GOIANIA",
    "Formosa": "GRUPO_FORMOSA",
    "Rio Verde": "GRUPO_RIO_VERDE",
    "Luziânia": "GRUPO_LUZIANIA",
    "Morrinhos": "GRUPO_MORRINHOS",
    "Iporá": "GRUPO_IPORA",
    "Montes Belos": "GRUPO_MONTES_BELOS",
    "Anápolis": "GRUPO_ANAPOLIS",
    "Uruaçu": "GRUPO_URUACU",
    "Metropolitana": "GRUPO_METROPOLITANA"
}

LIDERES_REGIONAIS = {
    "Goiânia": "LIDERES_GOIANIA",
    "Formosa": "LIDERES_FORMOSA",
    "Rio Verde": "LIDERES_RIO_VERDE",
    "Luziânia": "LIDERES_LUZIANIA",
    "Morrinhos": "LIDERES_MORRINHOS",
    "Iporá": "LIDERES_IPORA",
    "Montes Belos": "LIDERES_MONTES_BELOS",
    "Anápolis": "LIDERES_ANAPOLIS",
    "Uruaçu": "LIDERES_URUACU",
    "Metropolitana": "LIDERES_METROPOLITANA"
}

EXECUTIVOS_REGIONAIS = {
    "Goiânia": "EXECUTIVOS_GOIANIA",
    "Formosa": "EXECUTIVOS_FORMOSA",
    "Rio Verde": "EXECUTIVOS_RIO_VERDE",
    "Luziânia": "EXECUTIVOS_LUZIANIA",
    "Morrinhos": "EXECUTIVOS_MORRINHOS",
    "Iporá": "EXECUTIVOS_IPORA",
    "Montes Belos": "EXECUTIVOS_MONTES_BELOS",
    "Anápolis": "EXECUTIVOS_ANAPOLIS",
    "Uruaçu": "EXECUTIVOS_URUACU",
    "Metropolitana": "EXECUTIVOS_METROPOLITANA"
}

GERENTES_REGIONAIS = {
    "Goiânia": "GERENTES_GOIANIA",
    "Formosa": "GERENTES_FORMOSA",
    "Rio Verde": "GERENTES_RIO_VERDE",
    "Luziânia": "GERENTES_LUZIANIA",
    "Morrinhos": "GERENTES_MORRINHOS",
    "Iporá": "GERENTES_IPORA",
    "Montes Belos": "GERENTES_MONTES_BELOS",
    "Anápolis": "GERENTES_ANAPOLIS",
    "Uruaçu": "GERENTES_URUACU",
    "Metropolitana": "GERENTES_METROPOLITANA"
}


def verificar_pendencias():
    connection = conectar()
    cursor = connection.cursor()

    # Consulta SQL para verificar pendências
    with open("sql/pendencias_recursos_comunica.sql", "r") as file:
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


def enviar_mensagem_pendencias():

    hora_atual = datetime.now().time()

    if hora_atual >= datetime.strptime("05:00", "%H:%M").time() and hora_atual <= datetime.strptime("23:00", "%H:%M").time():
        pendencias = verificar_pendencias()

        ## verificando cache de ocorrencias já enviadas
        arquivo_cache = "cache_enviado/pendencias_comunica.json"

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

        for row in pendencias:
            idx, regional, ocorrencia, afetacao, info, tipo, minutos, status, prazo_comercial = row

            idx = str(idx)

            ocorrencias_banco.add(idx)

            ## Resgatando os grupos do whatsapp
            chave_env = MAPA_REGIONAIS.get(regional)

            if not chave_env:
                print(f"Regional '{regional}' não encontrada no mapa de grupos. Verifique a configuração.")
                continue

            id_whatsapp = safe_env_get(chave_env)
            marcados_whatsapp = []
            mensagem = ""

            ## ==========================================================
            ## NOVA OCORRÊNCIA
            ## ==========================================================
            if idx not in cache:

                ## nova ocorrência, adicionando ao cache com nível 1
                ## A mensagem NÃO será enviada agora.
                ## O sistema começará a contar o tempo a partir deste momento.
                nivel_atual = 1

                cache[idx] = {
                    "nivel": nivel_atual,
                    "status": status,
                    "regional": regional,
                    "ocorrencia": ocorrencia,
                    "cache_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                print(
                    f"Nova ocorrência cadastrada: {regional} "
                    f"(ID {idx}). Aguardando o tempo mínimo para envio."
                )

                ## Como é uma ocorrência nova, não envia mensagem nesta execução.
                continue

            ## ==========================================================
            ## OCORRÊNCIA JÁ EXISTENTE
            ## ==========================================================

            ## verificando se a ocorrencia já foi enviada e adicionando o nível de envio
            nivel_atual = cache[idx].get("nivel", 1)
            cache[idx]["status"] = status

            ## recuperando a última atualização
            try:
                ultima_atualizacao = datetime.strptime(
                    cache[idx]["ultima_atualizacao"],
                    "%Y-%m-%d %H:%M:%S"
                )
            except (KeyError, ValueError):
                ## Caso o cache antigo não possua uma data válida,
                ## considera a data atual para evitar envio imediato.
                ultima_atualizacao = datetime.now()

                cache[idx]["ultima_atualizacao"] = (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )

            tempo_decorrido = datetime.now() - ultima_atualizacao

            pode_enviar = False

            ## ==========================================================
            ## SOLICITAÇÃO DE PENDÊNCIA
            ## Só pode enviar após 2 HORAS da última atualização
            ## ==========================================================

            if status == 'Pendente':

                if tempo_decorrido >= timedelta(hours=2):
                    pode_enviar = True

                    ######### SOLICITAÇÃO DE PENDÊNCIA - AUMENTANDO O NÍVEL DE ENVIO CONFORME O TEMPO PASSA E ENVIANDO MENSAGEM

                    if nivel_atual < 3:
                        nivel_atual += 1

                    ## Atualiza a última atualização somente quando
                    ## realmente estiver liberando um novo envio.
                    cache[idx]["ultima_atualizacao"] = (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )

            ## ==========================================================
            ## SOLICITAÇÃO DE AGUARDANDO
            ## Só pode enviar após 3 HORAS da última atualização
            ## ==========================================================

            elif status == 'Aguardando':

                if tempo_decorrido >= timedelta(hours=3):
                    pode_enviar = True

                    ######### SOLICITAÇÃO DE AGUARDANDO - AUMENTANDO O NÍVEL DE ENVIO CONFORME O TEMPO PASSA E ENVIANDO MENSAGEM

                    if nivel_atual < 3:
                        nivel_atual += 1

                    ## Atualiza a última atualização somente quando
                    ## realmente estiver liberando um novo envio.
                    cache[idx]["ultima_atualizacao"] = (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )

            ## ==========================================================
            ## CASO AINDA NÃO TENHA PASSADO O TEMPO NECESSÁRIO
            ## NÃO ENVIA A MENSAGEM
            ## ==========================================================

            if not pode_enviar:

                minutos_decorridos = int(tempo_decorrido.total_seconds() / 60)

                if status == 'Pendente':
                    minutos_necessarios = 120

                elif status == 'Aguardando':
                    minutos_necessarios = 180

                else:
                    minutos_necessarios = 0

                if minutos_necessarios > 0:
                    minutos_restantes = max(
                        minutos_necessarios - minutos_decorridos,
                        0
                    )

                    print(
                        f"⏳ Ocorrência {idx} - {regional} ainda não será enviada. "
                        f"Status: {status}. "
                        f"Tempo decorrido: {minutos_decorridos} min. "
                        f"Faltam aproximadamente {minutos_restantes} min."
                    )

                continue

            ## ==========================================================
            ## RESGATANDO OS LÍDERES, EXECUTIVOS E GERENTES
            ## ==========================================================

            lideres = safe_env_get_split(
                safe_env_get(LIDERES_REGIONAIS.get(regional))
            )

            executivos = safe_env_get_split(
                safe_env_get(EXECUTIVOS_REGIONAIS.get(regional))
            )

            gerentes = safe_env_get_split(
                safe_env_get(GERENTES_REGIONAIS.get(regional))
            )

            if nivel_atual == 1:
                marcados_whatsapp = lideres

            elif nivel_atual == 2:
                marcados_whatsapp = lideres + executivos

            elif nivel_atual == 3:
                marcados_whatsapp = lideres + executivos + gerentes

            # remove vazios e duplicados
            marcados_whatsapp = list(
                set([m for m in marcados_whatsapp if m])
            )

            ## ==========================================================
            ## DESPACHANDO MENSAGEM EMERGENCIAL E COMERCIAL
            ## ==========================================================

            if tipo == 'Emergencial':
                mensagem = (
                    f"🚨 *Alerta Comunica COI - Recurso Status [{status.upper()}]*\n\n"
                    f" *Regional:* {regional.upper()}\n"
                    f" *ID:* {idx}\n"
                    f" *Ocorrência:* {ocorrencia}\n"
                    f" *Afetação:* {afetacao}\n"
                    f" *Tipo:* {tipo}\n"
                    f" *Aguardando:* {minutos} min\n"
                    f" *Solicitação:* {info if info else 'N/A'}"
                )
            else:
                mensagem = (
                    f"🚨 *Alerta Comunica COI - Recurso Status [{status.upper()}]*\n\n"
                    f" *Regional:* {regional.upper()}\n"
                    f" *ID:* {idx}\n"
                    f" *Ocorrência:* {ocorrencia}\n"
                    f" *Tipo:* {tipo}\n"
                    f" *Prazo Comercial:* {prazo_comercial}\n"
                    f" *Aguardando:* {minutos} min\n"
                    f" *Solicitação:* {info if info else 'N/A'}"
                )

            ## Atualizando o nível no cache
            cache[idx]["nivel"] = nivel_atual

            ## ==========================================================
            ## VERIFICANDO ID DO GRUPO WHATSAPP
            ## ==========================================================

            if id_whatsapp is None or id_whatsapp.strip() == "":
                print(
                    f"ID do grupo WhatsApp para a regional '{regional}' "
                    f"não encontrado. Verifique a configuração."
                )
                continue

            ## ==========================================================
            ## ENVIO DA MENSAGEM
            ## ==========================================================

            try:
                payload = {
                    "chatId": id_whatsapp,
                    "message": mensagem,
                    "mentions": marcados_whatsapp if marcados_whatsapp else [],
                    "regional": regional
                }

                res = requests.post(
                    safe_env_get("WA_SERVER_URL"),
                    json=payload,
                    timeout=10
                )

                if res.status_code == 200:
                    print(
                        f"✅ Nível {nivel_atual} enviado para "
                        f"{regional} (ID {idx})"
                    )

                else:
                    print(
                        f"Falha ao enviar mensagem para {regional} "
                        f"(ID {idx}). Status code: {res.status_code}, "
                        f"Response: {res.text}"
                    )

            except Exception as e:
                print(
                    f"Erro ao enviar mensagem para {regional} "
                    f"(ID {idx}): {e}"
                )

            sleep(1)

        ## removendo ocorrencias que não estão mais no banco de dados, para manter limpo
        cache = {
            idx: dados
            for idx, dados in cache.items()
            if idx in ocorrencias_banco
        }

        # Salva o cache atualizado
        with open(arquivo_cache, "w", encoding="utf-8") as arquivo:
            json.dump(cache, arquivo, ensure_ascii=False, indent=4)


# Loop agendado
schedule.every(1).minutes.do(enviar_mensagem_pendencias)

if __name__ == "__main__":
    enviar_mensagem_pendencias()

    while True:
        schedule.run_pending()
        time.sleep(1)
