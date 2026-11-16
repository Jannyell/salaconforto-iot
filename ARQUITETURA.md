# SalaConforto 1.5: arquitetura e dependências

Este documento descreve as peças da versão 1.5 e **tudo o que precisa ser instalado** para ela funcionar, com o papel
de cada dependência. O passo a passo de instalação e de início está no [README](README.md); o `python verificar.py`
confere quase tudo o que está listado aqui (ver a última coluna das tabelas).

## As peças

```
 SALAS                                   COMPUTADOR
 ┌──────────────────────┐   MQTT QoS 1   ┌─────────────┐        ┌──────────────┐        ┌─────────────────┐
 │ ESP32 + DHT22 (sala 1)│ ────────────▶ │ broker MQTT │ ─────▶ │ gravador.py  │ ─────▶ │ SQLite (WAL)    │
 │ simulador.py  (sala 2)│ sala/<id>/    │ (Mosquitto) │ ◀───── │ valida,      │        │ chave (sala,    │
 └──────────────────────┘   leitura      └─────────────┘ PUBACK │ calcula,     │        │  inicio, seq)   │
                                                                │ grava        │        └────────▲────────┘
                                                                └──────────────┘                 │ só lê
                                          ┌──────────────────┐   GET /api/...   ┌───────────────┴─┐
                                          │ painel Streamlit │ ───────────────▶ │ API Flask       │
                                          └──────────────────┘   a cada 5 s     └─────────────────┘
```

| Peça | Arquivo | O que faz |
|---|---|---|
| Placa (sala 1) | `firmware/` | Lê o DHT22 a cada 20 s, descarta leitura inválida (NaN), monta o JSON com `inicio` (número sorteado a cada ligada) e `seq` (contador) e publica em `sala/1/leitura` com QoS 1; sem a confirmação do broker (PUBACK) em 5 s, reenvia a mesma leitura uma vez, com o mesmo `seq` |
| Simulador (sala 2) | `dispositivo_simulador/simulador.py` | Faz o papel de outra placa, com valores aleatórios, em `sala/2/leitura` |
| Broker | `broker/mosquitto.conf` | Recebe as publicações, confirma cada uma (PUBACK) e entrega ao gravador; guarda mensagens e sessões em disco a cada 60 s e ao desligar |
| Gravador | `backend/gravador.py` | Assina `sala/+/leitura` com sessão persistente; confere a leitura, calcula a sensação térmica e grava; leitura repetida (mesma sala, `inicio`, `seq`) é ignorada; só confirma ao broker (PUBACK manual) depois de gravar ou de recusar de vez; num erro passageiro do banco (travado, disco cheio), não confirma, se desconecta e volta, e o broker entrega a mesma leitura de novo |
| Banco | `backend/data/medicoes.db` | SQLite em modo WAL: um escritor (o gravador) e vários leitores (a API) ao mesmo tempo |
| API | `backend/app.py`, `routes.py` | Só leitura: `GET /api/salas`, `/api/leituras?sala=`, `/api/leituras/ultima?sala=` |
| Painel | `frontend/dashboard.py` | Escolhe a sala, consulta a API a cada 5 s e mostra temperatura, umidade e sensação térmica |
| Checklist | `verificar.py` | Confere instalação, serviços e dados, e diz como resolver cada falha |

Ponto único de falha: o broker. Com ele fora, a placa não publica e as leituras daquele período se perdem; numa queda
abrupta, o último minuto que ele guardava pode se perder. Gravador, API e painel podem cair sem perder leituras (o broker guarda as do gravador até o limite da fila, por padrão 1000 mensagens: com duas salas a cada 20 s, cerca de 2 h 45 min). A placa também perde a leitura se o reenvio falhar (sem Wi-Fi ou sem broker): ela não guarda leituras para depois.

## Dependências instaladas

### No computador: Python e bibliotecas (`requirements.txt`)

| Dependência | Versão | Para que serve | Quem usa | Conferida pelo verificar.py |
|---|---|---|---|---|
| Python | 3.9 ou mais novo (testado no 3.12) | Roda gravador, simulador, API, painel e checklist | todos | sim |
| venv (ambiente virtual, vem com o Python) | — | Isola as bibliotecas do projeto das do sistema | todos | sim (aviso) |
| **paho-mqtt** | 2.2.0 | Cliente MQTT em Python: o gravador assina com QoS 1 e sessão persistente; o simulador e o checklist publicam | `gravador.py`, `simulador.py`, `verificar.py` | sim |
| **Flask** | 3.1.3 | Servidor HTTP da API de leitura | `backend/app.py`, `routes.py` | sim |
| **streamlit** | 1.67.0 | O painel no navegador (porta 8501) | `frontend/` | sim |
| **pandas** | 3.1.1 | Organiza as leituras em tabela para o painel | `frontend/` | sim |
| **altair** | 6.3.0 | Gráficos de temperatura, umidade e sensação térmica | `frontend/` | sim |
| **requests** | 2.34.2 | O painel consulta a API por HTTP | `frontend/dashboard.py` | sim |
| tzdata | 2026.6 | Base de fusos horários: o horário de cada leitura usa `America/Fortaleza`; no Windows, sem ela o `zoneinfo` não acha o fuso | `services/leitura_service.py`, `verificar.py` | indireta |
| sqlite3 (vem com o Python) | — | O banco de leituras; não precisa instalar servidor de banco | `services/armazenamento.py` | sim (lê o banco) |

As demais linhas do `requirements.txt` (Werkzeug, Jinja2, numpy, pyarrow, starlette, watchdog etc.) são
dependências das bibliotecas acima, instaladas junto pelo `pip install -r requirements.txt`; o projeto não as usa
diretamente.

### No computador: broker MQTT

| Dependência | Versão | Para que serve | Conferida pelo verificar.py |
|---|---|---|---|
| **Mosquitto** (`mosquitto`) | 2.0.18 (Ubuntu 24.04) | O broker MQTT: recebe as leituras das salas, confirma (PUBACK), guarda em disco e entrega ao gravador | sim (FALHA se faltar) |
| **mosquitto-clients** (`mosquitto_sub`, `mosquitto_pub`) | 2.0.18 | Ferramentas de linha de comando para ver as leituras passando (`mosquitto_sub -t "sala/#" -v`) e publicar testes | sim (aviso) |

Instalação: Linux `sudo apt install mosquitto mosquitto-clients`; Windows, instalador de mosquitto.org (já traz os
clientes). O serviço do sistema que o pacote sobe sozinho deve ser parado, para usar a configuração do projeto
(`mosquitto -c broker/mosquitto.conf -v`), que liga a persistência e aceita conexões da rede local.

### Para a placa real (sala 1)

Só faz falta para gravar o firmware na placa; sem eles, o sistema roda com o simulador. Por isso o checklist mostra
AVISO, e não FALHA, quando faltam.

| Dependência | Versão | Para que serve | Conferida pelo verificar.py |
|---|---|---|---|
| **arduino-cli** | 1.6.0 | Compila o firmware e grava na placa pelo terminal, sem abrir a Arduino IDE (`arduino-cli compile` / `upload`); também instala o suporte às placas e as bibliotecas. A Arduino IDE faz o mesmo pela interface | sim |
| **Suporte ao ESP32** (núcleo `esp32:esp32`, da Espressif) | 3.3.12 | Compilador, bibliotecas do ESP32 (Wi-Fi, por exemplo) e a ferramenta de gravação (esptool). Vem do índice `https://espressif.github.io/arduino-esp32/package_esp32_index.json`, que precisa ser adicionado antes; ocupa cerca de 6 GB em disco | sim |
| **DHT sensor library** (Adafruit) | 1.4.7 | Lê temperatura e umidade do sensor DHT22 | sim |
| **Adafruit Unified Sensor** | 1.1.15 | Dependência da DHT sensor library | sim |
| **MQTT** (Joel Gaehwiler, arduino-mqtt) | 2.5.3 | Cliente MQTT da placa: publica com **QoS 1** e espera o PUBACK do broker. A PubSubClient, mais comum, publica só com QoS 0 (sem confirmação), por isso não serve aqui | sim |
| Driver USB-serial da placa (CP210x ou CH340) | — | O computador reconhecer a placa pela USB. No Linux já vem no sistema (porta `/dev/ttyUSB0`, e o usuário precisa estar no grupo `dialout`); no Windows pode precisar instalar (porta `COM3`, `COM4`…) | não |

Resultado da compilação nesta máquina (`arduino-cli compile --fqbn esp32:esp32:esp32 firmware`): o firmware usa
906 KB (69%) da memória de programa e 47 KB (14%) da memória dinâmica.

Comandos (os mesmos do README):

```bash
arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32
arduino-cli lib install "DHT sensor library" "Adafruit Unified Sensor" "MQTT"
arduino-cli compile --fqbn esp32:esp32:esp32 firmware
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware
```

Antes de compilar, copie `firmware/credenciais.exemplo.h` para `firmware/credenciais.h` e preencha a rede Wi-Fi, o IP
do computador que roda o Mosquitto e a sala. O `credenciais.h` fica fora do git.

## Portas usadas

| Porta | Serviço |
|---|---|
| 1883 | Broker MQTT (Mosquitto), aberto à rede local para a placa alcançar |
| 5000 | API Flask (escuta em todas as interfaces, `0.0.0.0`, como no projeto original; o painel a consulta no próprio computador) |
| 8501 | Painel Streamlit |

A placa e o computador precisam estar na mesma rede, e o firewall do computador precisa liberar a porta 1883.
