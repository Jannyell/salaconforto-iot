# SalaConforto 1.5: arquitetura e dependências

Instalação e execução: [README](README.md). O `python verificar.py` confere as dependências abaixo.

## Peças

```
placa ESP32 + DHT22 (sala 1) ─┐
                              ├─ MQTT QoS 1 ─▶ broker ─▶ gravador ─▶ SQLite ◀─ API Flask ◀─ painel Streamlit
simulador.py (sala 2) ────────┘  sala/<id>/leitura      (PUBACK só depois de gravar)  (só lê)  (a cada 5 s)
```

| Peça | Arquivo | Papel |
|---|---|---|
| Placa | `firmware/` | Lê o DHT22 a cada 20 s e publica a leitura com `inicio` (sorteado a cada ligada) e `seq` (contador); sem PUBACK, reenvia uma vez |
| Simulador | `dispositivo_simulador/simulador.py` | Faz o papel de outra placa, na sala 2 |
| Broker | `broker/mosquitto.conf` | Recebe e confirma as leituras; guarda as do gravador em disco enquanto ele está fora |
| Gravador | `backend/gravador.py` | Valida, calcula a sensação térmica e grava; ignora a leitura repetida pela chave (sala, inicio, seq) |
| API | `backend/app.py`, `routes.py` | Só lê o banco |
| Painel | `frontend/dashboard.py` | Mostra a sala escolhida |

Ponto único de falha: o broker. Com ele fora, a placa não publica e as leituras se perdem.

## Dependências

| Dependência | Para que serve |
|---|---|
| Python 3.9+ e venv | Rodar os serviços com as bibliotecas isoladas |
| paho-mqtt | MQTT no Python: o gravador assina, o simulador publica |
| Flask · streamlit · pandas · altair · requests | API · painel · tabela · gráficos · consulta do painel à API |
| tzdata | Fuso horário das leituras (necessário no Windows) |
| Mosquitto e mosquitto-clients | O broker MQTT e as ferramentas para ver as mensagens |
| arduino-cli | Compilar e gravar o firmware pelo terminal (ou a Arduino IDE) |
| Suporte ao ESP32 (`esp32:esp32`) | Compilador e gravação para a placa |
| DHT sensor library + Adafruit Unified Sensor | Ler o DHT22 |
| MQTT (arduino-mqtt) | MQTT na placa, com QoS 1 (a PubSubClient só tem QoS 0) |

As quatro últimas só fazem falta para a placa real; sem elas, o sistema roda com o simulador.

## Portas

1883 (broker, aberto à rede local para a placa), 5000 (API), 8501 (painel).
