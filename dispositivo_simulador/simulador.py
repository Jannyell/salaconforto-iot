import json
import random
import time
import uuid

import paho.mqtt.client as mqtt

# Endereço do broker MQTT
BROKER_HOST = "127.0.0.1"
BROKER_PORTA = 1883

# O simulador publica pela sala 2 (a placa real usa a sala 1)
SALA = "2"
TOPICO = f"sala/{SALA}/leitura"

# Intervalo entre as medições:
INTERVALO = 20

# Identifica esta execução: junto com o seq, cada leitura fica única
INICIO = uuid.uuid4().hex[:8]


def gerar_leitura(seq):
    return {
        "inicio": INICIO,
        "seq": seq,
        # Hora da medida (segundos desde 1970): se a leitura esperar na fila, o banco guarda a hora certa
        "medida": int(time.time()),
        "temperatura": round(random.uniform(24, 34), 1),
        "umidade": round(random.uniform(40, 85), 1)
    }

def enviar_leitura(cliente, dados):

    # QoS 1: a biblioteca reenvia até o broker confirmar (PUBACK)
    info = cliente.publish(
        TOPICO,
        json.dumps(dados),
        qos=1
    )

    try:
        info.wait_for_publish(timeout=5)

    except RuntimeError:
        # Sem conexão: a biblioteca guarda a leitura e a envia quando reconectar
        print(f"Leitura {dados['seq']} sem conexão com o broker: guardada, sai quando ele voltar")
        print("-" * 35)
        return

    if info.is_published():
        print(f"Leitura {dados['seq']} publicada em {TOPICO} (broker confirmou)")
        print(f"Temperatura: {dados['temperatura']} °C")
        print(f"Umidade: {dados['umidade']} %")
        print("-" * 35)

    else:
        print(f"Leitura {dados['seq']} sem confirmação do broker: fica na fila e é reenviada")
        print("-" * 35)

def iniciar_simulador():

    print("Simulador SalaConforto iniciado!")
    print(f"Publicando em {TOPICO} a cada {INTERVALO} s (início {INICIO})")
    print("Pressione CTRL + C para encerrar.")
    print("-" * 35)

    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"salaconforto-simulador-{SALA}"
    )

    try:
        cliente.connect(BROKER_HOST, BROKER_PORTA, keepalive=60)

    except OSError as erro:
        print(f"Não foi possível conectar ao broker: {erro}")
        return

    cliente.loop_start()

    try:
        seq = 0
        while True:

            dados = gerar_leitura(seq)

            enviar_leitura(cliente, dados)

            seq += 1
            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        print("\nSimulador encerrado.")

    finally:
        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":
    iniciar_simulador()
