# SalaConforto

Sistema de monitoramento de temperatura, umidade e sensação térmica de qualquer ambiente: sala de aula, laboratório,
escritório, área de lazer, um cômodo da casa.

Cada sala tem uma placa ESP32 com um sensor DHT22, que publica as leituras num broker MQTT. Um gravador recebe as
leituras, calcula a sensação térmica e grava num banco SQLite. A API Flask lê o banco, e o painel Streamlit mostra
cada sala.

Na demonstração, a **sala 1** é a placa real e a **sala 2** é o simulador. Os dois podem rodar ao mesmo tempo.

## Arquitetura

```
placa ESP32 + DHT22 (sala 1) ─┐
                              ├─ MQTT · QoS 1 ─▶ Mosquitto ─▶ gravador.py ─▶ SQLite ◀─ API Flask ◀─ painel Streamlit
simulador.py (sala 2) ────────┘   sala/<id>/leitura           valida, calcula      só leitura    a cada 5 s
                                                              e grava
```

| Peça | Arquivo | Responsabilidade |
|---|---|---|
| Placa | `firmware/` | lê o DHT22 e publica `{"inicio", "seq", "temperatura", "umidade"}` em `sala/1/leitura` |
| Simulador | `dispositivo_simulador/simulador.py` | publica leituras aleatórias em `sala/2/leitura` |
| Broker | `broker/mosquitto.conf` | recebe e entrega as mensagens; guarda as do gravador enquanto ele estiver fora do ar |
| Gravador | `backend/gravador.py` | assina `sala/+/leitura`, valida, calcula a sensação térmica e grava no SQLite |
| Banco | `backend/data/medicoes.db` | uma linha por leitura; a chave `(sala, inicio, seq)` descarta leituras repetidas |
| API | `backend/app.py` | só lê o banco: `GET /api/salas`, `GET /api/leituras?sala=1`, `GET /api/leituras/ultima?sala=1` |
| Painel | `frontend/dashboard.py` | mostra a sala escolhida e compara a sensação com o limite |

`inicio` identifica cada vez que a placa (ou o simulador) liga, e `seq` conta as leituras desde então. Juntos, eles
identificam a leitura: se o broker entregar a mesma leitura duas vezes, o banco grava uma só.

## 1. Instalar

### Python e bibliotecas

```bash
git clone URL_DO_REPOSITORIO
cd SalaConforto
python -m venv venv
```

Ative o ambiente virtual:

```powershell
.\venv\Scripts\Activate.ps1
```

No Linux ou no macOS:

```bash
source venv/bin/activate
```

Instale as bibliotecas:

```bash
pip install -r requirements.txt
```

### Broker MQTT (Mosquitto)

- **Windows:** baixe o instalador em https://mosquitto.org/download/ e adicione a pasta de instalação ao PATH.
- **Linux (Ubuntu/Debian):**

  ```bash
  sudo apt install mosquitto mosquitto-clients
  ```

  O pacote do Linux sobe o Mosquitto como serviço do sistema, na porta 1883. Pare esse serviço antes de usar a
  configuração do projeto:

  ```bash
  sudo systemctl stop mosquitto
  ```

## 2. Executar

Abra um terminal para cada serviço, sempre na pasta do projeto e com o ambiente virtual ativado. A ordem importa: o
broker e o gravador sobem primeiro, assim nenhuma leitura se perde enquanto o resto inicia.

| Terminal | Serviço | Comando |
|---|---|---|
| 1 | Broker | `mosquitto -c broker/mosquitto.conf -v` |
| 2 | Gravador | `python backend/gravador.py` |
| 3 | API | `python backend/app.py` |
| 4 | Simulador (sala 2) | `python dispositivo_simulador/simulador.py` |
| 5 | Painel | `streamlit run frontend/dashboard.py` |

**Importante:** mantenha os terminais abertos durante a execução do projeto.

### O que cada terminal mostra

```
[gravador 17:22:38] Conectado ao broker 127.0.0.1:1883, assinando sala/+/leitura
[gravador 17:23:09] sala 2 · seq 0 · 29.4 °C · 83.8 % → sensação 36.8 °C · gravada
[gravador 17:23:10] sala 1 · seq 0 · repetida, ignorada
[gravador 17:23:11] sala 1 · recusada: Temperatura fora da faixa do sensor
[api 17:23:12] GET /api/leituras?sala=2 → 1 leitura(s) de hoje
Leitura 0 publicada em sala/2/leitura (broker confirmou)
```

### Checklist rápido

Confere a instalação (Python, bibliotecas, Mosquitto e, para a placa real, o arduino-cli, o suporte ao ESP32 e as
bibliotecas do firmware), os serviços e se as leituras estão chegando, e diz como resolver cada falha:

```bash
python verificar.py
```

Com `--ponta-a-ponta`, ele também publica uma leitura de teste e confere se ela passa por broker, gravador, banco e
API (a leitura de teste é apagada no fim):

```bash
python verificar.py --ponta-a-ponta
```

### Conferir o funcionamento

Ver as leituras passando pelo broker:

```bash
mosquitto_sub -h localhost -t "sala/#" -v
```

Ver o que está gravado no banco:

```bash
sqlite3 backend/data/medicoes.db "SELECT sala, seq, horario, temperatura, umidade, sensacao_termica FROM leituras ORDER BY horario DESC LIMIT 10"
```

Se o gravador cair, as leituras ficam guardadas no broker e chegam quando ele volta: o terminal 2 mostra
"Reconectado ao broker; mensagens guardadas durante a queda chegam agora".

## 3. Placa real (sala 1)

1. Na Arduino IDE, instale o suporte às placas **ESP32** (Espressif) e as bibliotecas:
   - **DHT sensor library** (Adafruit), com a dependência **Adafruit Unified Sensor**;
   - **MQTT** (Joel Gaehwiler), que publica com QoS 1. A PubSubClient publica só com QoS 0.
2. Ligue o DHT22: alimentação em 3,3 V, terra em GND e dados no **GPIO 17**. O sensor avulso precisa de um resistor de
   10 kΩ entre dados e 3,3 V; os módulos prontos já vêm com ele.
3. Copie `firmware/credenciais.exemplo.h` para `firmware/credenciais.h` e preencha a rede Wi-Fi, o IP do computador
   que roda o Mosquitto (`MQTT_HOST`) e a sala (`SALA_ID`). O `credenciais.h` fica fora do git.
4. Abra `firmware/firmware.ino`, escolha a placa ESP32 e a porta, e envie.

   Pelo terminal, sem a IDE, o [arduino-cli](https://arduino.github.io/arduino-cli/) faz o mesmo
   (`python verificar.py` confere se ele, o suporte ao ESP32 e as bibliotecas estão instalados):

   ```bash
   arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
   arduino-cli core update-index
   arduino-cli core install esp32:esp32
   arduino-cli lib install "DHT sensor library" "Adafruit Unified Sensor" "MQTT"
   arduino-cli compile --fqbn esp32:esp32:esp32 firmware
   arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware
   ```

   No Windows, a porta é `COM3`, `COM4`…; `arduino-cli board list` mostra qual.
5. No monitor serial (115200), a placa mostra a conexão ao Wi-Fi, ao broker e cada leitura publicada.

O computador e a placa precisam estar na mesma rede. A configuração do broker aceita conexões da rede local sem senha;
isso serve para demonstração, não para uma rede aberta.

## Arquitetura e dependências

[ARQUITETURA.md](ARQUITETURA.md) descreve cada peça e lista tudo o que precisa ser instalado (bibliotecas Python,
Mosquitto, arduino-cli, suporte ao ESP32 e bibliotecas do firmware), com o papel de cada uma.

## Estrutura

```
backend/       app.py e routes.py (API), gravador.py, services/ (regras, cálculo, banco), data/ (banco SQLite)
broker/        mosquitto.conf
dispositivo_simulador/   simulador.py
firmware/      firmware.ino, sensor, wificonector, mqttpublicador, credenciais.exemplo.h
frontend/      dashboard.py e componentes do painel
```
