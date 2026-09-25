from modulos.pendencias_recursos_comunica import enviar_mensagem_pendencias
from modulos.ocorrencias_afetacao import enviar_mensagem_ocorrencia_afetacao
import schedule
from time import sleep

def executar_ocorrencias():
    try:
        enviar_mensagem_ocorrencia_afetacao()
    except Exception as e:
        print(f"Erro em ocorrencias_afetacao: {e}")


def executar_pendencias():
    try:
        enviar_mensagem_pendencias()
    except Exception as e:
        print(f"Erro em pendencias_recursos_comunica: {e}")

schedule.every(1).minutes.do(executar_ocorrencias)
schedule.every(1).minutes.do(executar_pendencias)

if __name__ == "__main__":
    executar_ocorrencias()
    executar_pendencias()

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            print(f"Erro no scheduler: {e}")

        sleep(1)
