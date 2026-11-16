"""
Checklist do SalaConforto: confere, em poucos segundos, se o ambiente e os serviços estão prontos.

Uso, na pasta do projeto e com o ambiente virtual ativado:
    python verificar.py                  # instalação e serviços
    python verificar.py --ponta-a-ponta  # também publica uma leitura de teste e confere se ela chega à API

Cada item mostra OK, AVISO ou FALHA e, quando falha, como resolver.
"""

import importlib
import json
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# --------------------------------------
# CONFIGURAÇÕES
# --------------------------------------

RAIZ = Path(__file__).resolve().parent

BROKER_HOST = "127.0.0.1"
BROKER_PORTA = 1883
URL_API = "http://127.0.0.1:5000"
URL_PAINEL = "http://127.0.0.1:8501"
BANCO = RAIZ / "backend" / "data" / "medicoes.db"

# Bibliotecas do requirements.txt usadas diretamente pelo projeto
BIBLIOTECAS = {
    "flask": "Flask",
    "streamlit": "streamlit",
    "pandas": "pandas",
    "altair": "altair",
    "requests": "requests",
    "paho.mqtt.client": "paho-mqtt",
}

# Placa real: suporte ao ESP32 e bibliotecas do firmware (instaladas pelo arduino-cli)
NUCLEO_ESP32 = "esp32:esp32"
BIBLIOTECAS_FIRMWARE = ["DHT sensor library", "Adafruit Unified Sensor", "MQTT"]

# Uma leitura é "recente" se chegou nos últimos 2 minutos (o envio é a cada 20 s)
RECENTE_SEGUNDOS = 120

resultados = {"OK": 0, "AVISO": 0, "FALHA": 0}


def item(estado, texto, dica=None):
    resultados[estado] += 1
    marca = {"OK": "✓", "AVISO": "!", "FALHA": "✗"}[estado]
    print(f"  {marca} {estado:<5} {texto}")
    if dica and estado != "OK":
        print(f"          → {dica}")


def secao(titulo):
    print(f"\n{titulo}")


def porta_aberta(host, porta):
    try:
        with socket.create_connection((host, porta), timeout=2):
            return True
    except OSError:
        return False


def ip_na_rede():
    # Descobre o IP deste computador na rede local (a interface da rota padrão).
    # O UDP "connect" não envia nada: só escolhe a interface de saída
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def get_json(url):
    with urllib.request.urlopen(url, timeout=3) as resposta:
        return resposta.status, json.loads(resposta.read())


# --------------------------------------
# 1. INSTALAÇÃO
# --------------------------------------

def verificar_instalacao():

    secao("1. Instalação")

    versao = sys.version_info
    if versao >= (3, 9):
        item("OK", f"Python {versao.major}.{versao.minor}")
    else:
        item("FALHA", f"Python {versao.major}.{versao.minor}", "use o Python 3.9 ou mais novo")

    if sys.prefix != sys.base_prefix:
        item("OK", "ambiente virtual ativado")
    else:
        item("AVISO", "ambiente virtual não está ativado",
             r"ative com .\venv\Scripts\Activate.ps1 (Windows) ou source venv/bin/activate (Linux)")

    for modulo, pacote in BIBLIOTECAS.items():
        try:
            importlib.import_module(modulo)
            item("OK", f"biblioteca {pacote}")
        except ImportError:
            item("FALHA", f"biblioteca {pacote} não instalada", "pip install -r requirements.txt")

    if shutil.which("mosquitto"):
        item("OK", "Mosquitto instalado")
    else:
        item("FALHA", "Mosquitto não encontrado no PATH",
             "Linux: sudo apt install mosquitto mosquitto-clients · Windows: instalador de mosquitto.org")

    if shutil.which("mosquitto_sub"):
        item("OK", "mosquitto_sub instalado (para ver as leituras passando)")
    else:
        item("AVISO", "mosquitto_sub não encontrado", "Linux: sudo apt install mosquitto-clients")

    if (RAIZ / "broker" / "mosquitto.conf").exists():
        item("OK", "broker/mosquitto.conf")
    else:
        item("FALHA", "broker/mosquitto.conf não existe", "restaure o arquivo do repositório")

    if (RAIZ / "firmware" / "credenciais.h").exists():
        item("OK", "firmware/credenciais.h (placa real)")
    else:
        item("AVISO", "firmware/credenciais.h não existe (só faz falta para a placa real)",
             "copie firmware/credenciais.exemplo.h para firmware/credenciais.h e preencha")


def arduino_cli_json(*argumentos):
    resultado = subprocess.run(["arduino-cli", *argumentos, "--format", "json"],
                               capture_output=True, text=True, timeout=30)
    return json.loads(resultado.stdout or "{}")


# --------------------------------------
# 1b. PLACA REAL (FIRMWARE)
# --------------------------------------

def verificar_firmware():

    secao("1b. Placa real: arduino-cli, suporte ao ESP32 e bibliotecas do firmware")

    if not shutil.which("arduino-cli"):
        item("AVISO", "arduino-cli não encontrado no PATH (só faz falta para gravar a placa real)",
             "instale pelo site arduino.github.io/arduino-cli e confira se a pasta dele está no PATH")
        return

    item("OK", "arduino-cli instalado")

    try:
        plataformas = arduino_cli_json("core", "list").get("platforms", [])
        instaladas = {p.get("id"): p.get("installed_version") for p in plataformas}
    except (OSError, ValueError, subprocess.SubprocessError):
        instaladas = {}

    if NUCLEO_ESP32 in instaladas:
        item("OK", f"suporte ao ESP32 ({NUCLEO_ESP32} {instaladas[NUCLEO_ESP32]})")
    else:
        item("AVISO", "suporte ao ESP32 não instalado",
             "arduino-cli config add board_manager.additional_urls "
             "https://espressif.github.io/arduino-esp32/package_esp32_index.json && "
             "arduino-cli core update-index && arduino-cli core install esp32:esp32")

    try:
        bibliotecas = arduino_cli_json("lib", "list").get("installed_libraries", [])
        nomes = {b.get("library", {}).get("name") for b in bibliotecas}
    except (OSError, ValueError, subprocess.SubprocessError):
        nomes = set()

    for nome in BIBLIOTECAS_FIRMWARE:
        if nome in nomes:
            item("OK", f"biblioteca do firmware {nome}")
        else:
            item("AVISO", f"biblioteca do firmware {nome} não instalada", f'arduino-cli lib install "{nome}"')


# --------------------------------------
# 2. SERVIÇOS
# --------------------------------------

def verificar_servicos():

    secao("2. Serviços")

    if porta_aberta(BROKER_HOST, BROKER_PORTA):
        item("OK", f"broker respondendo em {BROKER_HOST}:{BROKER_PORTA}")
    else:
        item("FALHA", "broker fora do ar", "terminal 1: mosquitto -c broker/mosquitto.conf -v")

    try:
        status, _ = get_json(f"{URL_API}/")
        item("OK", f"API respondendo em {URL_API} ({status})")
    except Exception:
        item("FALHA", "API fora do ar", "terminal 3: python backend/app.py")

    if porta_aberta("127.0.0.1", 8501):
        item("OK", f"painel respondendo em {URL_PAINEL}")
    else:
        item("FALHA", "painel fora do ar", "terminal 5: streamlit run frontend/dashboard.py")

    try:
        ip = ip_na_rede()
        item("OK", f"IP deste computador na rede: {ip} (MQTT_HOST da placa; painel em http://{ip}:8501)")
        if not porta_aberta(ip, BROKER_PORTA):
            item("AVISO", f"broker não responde em {ip}:{BROKER_PORTA}; a placa não vai alcançá-lo",
                 "suba o broker com -c broker/mosquitto.conf (ele abre a porta para a rede)")
    except OSError:
        item("AVISO", "sem rede: não foi possível descobrir o IP deste computador",
             "conecte o computador ao mesmo Wi-Fi da placa")


# --------------------------------------
# 3. DADOS
# --------------------------------------

def verificar_dados():

    secao("3. Dados (gravador, simulador e placa)")

    if not BANCO.exists():
        item("FALHA", "banco ainda não existe",
             "suba o gravador (terminal 2: python backend/gravador.py) e um publicador")
        return

    with sqlite3.connect(BANCO) as conexao:
        linhas = conexao.execute(
            "SELECT sala, MAX(horario), COUNT(*) FROM leituras GROUP BY sala ORDER BY sala"
        ).fetchall()

    if not linhas:
        item("AVISO", "banco existe, mas sem leituras", "confira o gravador e o simulador")
        return

    agora = datetime.now(ZoneInfo("America/Fortaleza"))
    nomes = {"1": "placa real", "2": "simulador"}

    for sala, ultima, total in linhas:
        idade = (agora - datetime.fromisoformat(ultima)).total_seconds()
        texto = f"sala {sala} ({nomes.get(sala, 'outra')}): {total} leitura(s), a última há {idade:.0f} s"
        if idade <= RECENTE_SEGUNDOS:
            item("OK", texto)
        else:
            dica = ("confira o terminal do simulador" if sala == "2"
                    else "confira o monitor serial da placa (Wi-Fi, IP do broker, sala)")
            item("AVISO", texto + " (parada?)", dica + " e o terminal do gravador")


# --------------------------------------
# 4. PONTA A PONTA (opcional)
# --------------------------------------

def verificar_ponta_a_ponta():

    secao("4. Ponta a ponta: publica uma leitura de teste na sala 'teste'")

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        item("FALHA", "sem paho-mqtt para publicar", "pip install -r requirements.txt")
        return

    leitura = {"inicio": uuid.uuid4().hex[:8], "seq": 0, "temperatura": 25.0, "umidade": 50.0}

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"salaconforto-verificar-{leitura['inicio']}")
    try:
        cliente.connect(BROKER_HOST, BROKER_PORTA, keepalive=30)
    except OSError:
        item("FALHA", "não conectou ao broker", "suba o broker antes")
        return

    cliente.loop_start()
    info = cliente.publish("sala/teste/leitura", json.dumps(leitura), qos=1)
    info.wait_for_publish(timeout=5)
    cliente.loop_stop()
    cliente.disconnect()

    if info.is_published():
        item("OK", "broker confirmou a publicação (PUBACK)")
    else:
        item("FALHA", "broker não confirmou a publicação")
        return

    # Espera o gravador gravar e a API devolver
    for _ in range(10):
        time.sleep(0.5)
        try:
            _, leituras = get_json(f"{URL_API}/api/leituras?sala=teste")
        except Exception:
            item("FALHA", "API fora do ar", "terminal 3: python backend/app.py")
            return
        if leituras:
            item("OK", "a leitura de teste passou por broker → gravador → banco → API")

            # Apaga a leitura de teste, para ela não aparecer no painel
            with sqlite3.connect(BANCO) as conexao:
                conexao.execute("DELETE FROM leituras WHERE sala = 'teste'")
            return

    item("FALHA", "a leitura de teste não chegou à API em 5 s",
         "confira o terminal do gravador (terminal 2): ele precisa estar conectado ao broker")


# --------------------------------------
# EXECUÇÃO
# --------------------------------------

if __name__ == "__main__":

    print("Checklist SalaConforto")

    verificar_instalacao()
    verificar_firmware()
    verificar_servicos()
    verificar_dados()

    if "--ponta-a-ponta" in sys.argv:
        verificar_ponta_a_ponta()

    print(f"\nResumo: {resultados['OK']} OK · {resultados['AVISO']} aviso(s) · {resultados['FALHA']} falha(s)")

    sys.exit(1 if resultados["FALHA"] else 0)
