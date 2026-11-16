import json
import sqlite3
import time
from datetime import datetime

import paho.mqtt.client as mqtt

import services.leitura_service as service


# --------------------------------------
# CONFIGURAÇÕES
# --------------------------------------

BROKER_HOST = "127.0.0.1"
BROKER_PORTA = 1883

# Tópico de cada sala: sala/<id>/leitura
TOPICO = "sala/+/leitura"

# Identificador fixo: com ele o broker guarda as mensagens
# enquanto o gravador estiver fora do ar (sessão persistente)
ID_CLIENTE = "salaconforto-gravador"


def log(mensagem):
    print(f"[gravador {datetime.now():%H:%M:%S}] {mensagem}", flush=True)


# --------------------------------------
# CONEXÃO COM O BROKER
# --------------------------------------

def ao_conectar(cliente, dados, flags, codigo, propriedades):

    if codigo.is_failure:
        log(f"Falha ao conectar ao broker: {codigo}")
        return

    # QoS 1: cada mensagem é entregue pelo menos uma vez
    cliente.subscribe(TOPICO, qos=1)

    if flags.session_present:
        log(f"Reconectado ao broker; mensagens guardadas durante a queda chegam agora")
    else:
        log(f"Conectado ao broker {BROKER_HOST}:{BROKER_PORTA}, assinando {TOPICO}")


def ao_desconectar(cliente, dados, flags, codigo, propriedades):
    log(f"Desconectado do broker ({codigo}); tentando reconectar...")


# --------------------------------------
# CADA LEITURA RECEBIDA
# --------------------------------------

def ao_receber(cliente, dados, mensagem):

    # sala/<id>/leitura → <id>
    sala = mensagem.topic.split("/")[1]

    try:
        leitura = json.loads(mensagem.payload)

    except ValueError:
        log(f"sala {sala} · recusada: JSON inválido")
        confirmar(cliente, mensagem)
        return

    try:
        resultado, status = service.registrar_leitura(sala, leitura)

    except (sqlite3.OperationalError, OSError) as erro:
        # Erro passageiro (banco travado, disco cheio, falha de escrita): NÃO confirma.
        # O gravador se desconecta e volta; o broker entrega a mesma leitura de novo
        log(f"sala {sala} · erro ao gravar ({erro}); sem confirmação, o broker entrega de novo")
        cliente.disconnect()
        return

    except Exception as erro:
        # Erro inesperado com esta leitura: tentar de novo daria o mesmo erro.
        # Registra, confirma (descarta) e segue, para não travar as próximas
        log(f"sala {sala} · erro inesperado ({erro}); leitura descartada")
        confirmar(cliente, mensagem)
        return

    if status == 201:
        d = resultado["dados"]
        log(
            f"sala {sala} · seq {d['seq']} · {d['temperatura']:.1f} °C · {d['umidade']:.1f} % "
            f"→ sensação {d['sensacao_termica']:.1f} °C · gravada"
        )

    elif status == 200:
        log(f"sala {sala} · seq {leitura.get('seq')} · repetida, ignorada")

    else:
        log(f"sala {sala} · recusada: {resultado['erro']}")

    # Só agora o gravador confirma o recebimento ao broker (PUBACK):
    # a leitura já foi gravada (ou recusada de vez)
    confirmar(cliente, mensagem)


def confirmar(cliente, mensagem):
    # Confirmação manual (manual_ack=True): o PUBACK sai aqui, e não sozinho ao fim de ao_receber
    cliente.ack(mensagem.mid, mensagem.qos)


def iniciar_gravador():

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=ID_CLIENTE,
        clean_session=False,
        manual_ack=True
    )

    cliente.on_connect = ao_conectar
    cliente.on_disconnect = ao_desconectar
    cliente.on_message = ao_receber

    log("Gravador SalaConforto iniciado!")
    log("Pressione CTRL + C para encerrar.")

    try:
        cliente.connect(BROKER_HOST, BROKER_PORTA, keepalive=60)

        while True:
            cliente.loop_forever(retry_first_connection=True)

            # O loop só termina quando o gravador se desconecta de propósito (erro ao gravar):
            # espera um pouco e reconecta; o broker entrega de novo o que não foi confirmado
            time.sleep(2)
            log("Reconectando ao broker...")
            try:
                cliente.reconnect()
            except OSError as erro:
                log(f"Broker indisponível ({erro}); tentando de novo...")

    except KeyboardInterrupt:
        log("Gravador encerrado.")

    except OSError as erro:
        log(f"Não foi possível conectar ao broker: {erro}")


if __name__ == "__main__":
    iniciar_gravador()
