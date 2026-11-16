# SalaConforto

Monitora temperatura, umidade e sensação térmica de qualquer sala. Na demonstração, a **sala 1** é a placa real
(ESP32 + DHT22) e a **sala 2** é o simulador. Peças e dependências: [ARQUITETURA.md](ARQUITETURA.md).

```
placa (sala 1) e simulador (sala 2) ─MQTT─▶ Mosquitto ─▶ gravador ─▶ SQLite ◀─ API Flask ◀─ painel Streamlit
```

## Instalar

```bash
git clone git@github.com:edytarcio/salaconforto-iot.git
cd salaconforto-iot
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Mosquitto: no Linux, `sudo apt install mosquitto mosquitto-clients` e depois `sudo systemctl stop mosquitto` (o projeto
usa a própria configuração); no Windows, o instalador de mosquitto.org, com a pasta no PATH.

## Executar

Um terminal por linha, na pasta do projeto, com o venv ativado, nesta ordem:

```bash
mosquitto -c broker/mosquitto.conf -v
python backend/gravador.py
python backend/app.py
python dispositivo_simulador/simulador.py
streamlit run frontend/dashboard.py
```

Para conferir a instalação, os serviços e as leituras (diz como resolver cada falha):

```bash
python verificar.py
```

## Placa real (sala 1)

1. DHT22: 3,3 V, GND e dados no **GPIO 17** (o sensor avulso precisa de um resistor de 10 kΩ entre dados e 3,3 V).
2. Copie `firmware/credenciais.exemplo.h` para `firmware/credenciais.h` (fica fora do git) e preencha a rede Wi-Fi
   (2,4 GHz), o IP do computador do broker (`MQTT_HOST`; reserve um IP fixo no roteador) e a sala (`SALA_ID`, um
   número diferente por placa).
3. Compile e grave pela Arduino IDE ou pelo arduino-cli (porta no Windows: `COM3`, `COM4`…; veja `arduino-cli board list`):

```bash
arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index && arduino-cli core install esp32:esp32
arduino-cli lib install "DHT sensor library" "Adafruit Unified Sensor" "MQTT"
arduino-cli compile --fqbn esp32:esp32:esp32 firmware
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware
```

A placa e o computador precisam estar na mesma rede, com a porta 1883 liberada no firewall. O broker aceita conexões
da rede local sem senha: serve para demonstração, não para uma rede aberta.
