# SalaConforto

Monitora temperatura, umidade e sensação térmica de qualquer sala. Na demonstração, a **sala 1** é a placa real
(ESP32 + DHT22) e a **sala 2** é o simulador. Peças e dependências: [ARQUITETURA.md](ARQUITETURA.md).

```
placa (sala 1) e simulador (sala 2) ─MQTT─▶ Mosquitto ─▶ gravador ─▶ SQLite ◀─ API Flask ◀─ painel Streamlit
```

## Instalar

Pré-requisitos: Git, Python 3.9+ e Mosquitto.

- **Linux:** `sudo apt install mosquitto mosquitto-clients` e depois `sudo systemctl stop mosquitto` (o projeto usa a
  própria configuração).
- **Windows:** instalador de mosquitto.org, com a pasta no PATH; depois, num PowerShell de administrador,
  `net stop mosquitto` (o instalador também sobe um serviço na mesma porta).

```bash
git clone https://github.com/edytarcio/salaconforto-iot.git
cd salaconforto-iot
python3 -m venv venv              # Windows: python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Executar

Um terminal por linha, na pasta do projeto, com o venv ativado, nesta ordem:

```bash
mosquitto -c broker/mosquitto.conf -v
python backend/gravador.py
python backend/app.py
python dispositivo_simulador/simulador.py
streamlit run frontend/dashboard.py
```

Painel: http://localhost:8501. Escolha a sala 2: chega uma leitura a cada 20 s.

## Validar

Num 6º terminal, com o venv ativado:

```bash
python verificar.py --ponta-a-ponta
```

Deve terminar sem falhas; se algo falhar, ele diz o comando que resolve. Sem placa real, dois avisos são normais:
falta de `credenciais.h` e sala 1 parada. Ele também mostra o **IP deste computador na rede**, usado abaixo.

## Rede (qualquer Wi-Fi)

O computador que roda os serviços e os outros aparelhos (a placa, ou um celular abrindo o painel) precisam estar na
**mesma rede**. Nela, o painel abre em `http://<IP do computador>:8501` e a placa usa esse IP como broker.

- **Firewall do computador:** libere as portas 1883 (broker) e 8501 (painel).
  - Linux, se o ufw estiver ativo: `sudo ufw allow 1883,8501/tcp`
  - Windows (PowerShell de administrador):
    `New-NetFirewallRule -DisplayName SalaConforto -Direction Inbound -Protocol TCP -LocalPort 1883,8501 -Action Allow`
- **Redes que não servem:** as que isolam os aparelhos entre si (rede de visitantes, de hotel, de muitas faculdades) e
  as que pedem login (página de acesso ou usuário e senha, como a eduroam). Nesses casos, use o **roteador do celular**
  e conecte o computador e a placa a ele.
- **Trocou de rede?** O IP do computador muda: rode o `verificar.py`, atualize o `MQTT_HOST` da placa e grave de novo.

O broker aceita conexões da rede sem senha: serve para demonstração, não para uma rede aberta.

## Placa real (sala 1)

1. DHT22: 3,3 V, GND e dados no **GPIO 17** (o sensor avulso precisa de um resistor de 10 kΩ entre dados e 3,3 V).
2. Copie `firmware/credenciais.exemplo.h` para `firmware/credenciais.h` (fica fora do git) e preencha a rede Wi-Fi
   (2,4 GHz; o ESP32 não conecta em 5 GHz), o IP do computador (`MQTT_HOST`; reserve um IP fixo no roteador, se puder)
   e a sala (`SALA_ID`, um número diferente por placa; a 2 é do simulador).
3. Compile e grave pela Arduino IDE ou pelo arduino-cli (porta no Windows: `COM3`, `COM4`…; veja `arduino-cli board list`):

```bash
arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index && arduino-cli core install esp32:esp32
arduino-cli lib install "DHT sensor library" "Adafruit Unified Sensor" "MQTT"
arduino-cli compile --fqbn esp32:esp32:esp32 firmware
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware
```

No monitor serial (115200), a placa mostra a conexão ao Wi-Fi, ao broker e cada leitura publicada.
