
#include "mqttpublicador.h"

#include <WiFi.h>
#include <MQTT.h>

#include "credenciais.h"

// --------------------------------------
// CLIENTE MQTT
// --------------------------------------

// Biblioteca "MQTT" de Joel Gaehwiler (arduino-mqtt):
// publica com QoS 1 e espera a confirmação do broker (PUBACK)
static WiFiClient rede;
static MQTTClient cliente(256);

// --------------------------------------
// INICIA O CLIENTE
// --------------------------------------

void MqttPublicador::iniciar() {

    // Identifica esta inicialização da placa: junto com o seq,
    // cada leitura fica única mesmo depois de a placa reiniciar
    inicio = String(esp_random(), HEX);

    cliente.begin(MQTT_HOST, MQTT_PORTA, rede);

    // keepalive de 60 s, sessão limpa, espera de até 5 s pela confirmação
    cliente.setOptions(60, true, 5000);

    reconectar();
}

// --------------------------------------
// VERIFICA E REFAZ A CONEXÃO
// --------------------------------------

bool MqttPublicador::conectado() {

    return cliente.connected();
}

bool MqttPublicador::reconectar() {

    Serial.print("Conectando ao broker MQTT ");
    Serial.print(MQTT_HOST);
    Serial.print(":");
    Serial.println(MQTT_PORTA);

    String id = String("salaconforto-placa-") + SALA_ID;

    if (cliente.connect(id.c_str())) {

        Serial.println("Broker conectado!");
        return true;
    }

    Serial.println("Falha ao conectar ao broker.");
    return false;
}

// --------------------------------------
// MANTÉM A CONEXÃO VIVA (chamar no loop)
// --------------------------------------

void MqttPublicador::manter() {

    cliente.loop();
}

// --------------------------------------
// HORA CERTA (NTP)
// --------------------------------------

// O relógio da placa só vale depois de acertado pela internet (NTP)
static bool relogioCerto() {

    return time(nullptr) > 1700000000;
}

// --------------------------------------
// MONTA UMA LEITURA NOVA
// --------------------------------------

Leitura MqttPublicador::novaLeitura(float temperatura, float umidade) {

    Leitura leitura;

    strncpy(leitura.inicio, inicio.c_str(), sizeof(leitura.inicio) - 1);
    leitura.inicio[sizeof(leitura.inicio) - 1] = '\0';

    // O seq avança a cada leitura e nunca se repete na mesma ligada
    leitura.seq = seq++;

    leitura.temperatura = temperatura;
    leitura.umidade = umidade;

    // Hora da medida: se o relógio ainda não foi acertado, ela é calculada na publicação
    leitura.medida = relogioCerto() ? (uint32_t) time(nullptr) : 0;
    leitura.ms = millis();

    return leitura;
}

// --------------------------------------
// PUBLICA UMA LEITURA
// --------------------------------------

bool MqttPublicador::publicar(Leitura &leitura) {

    // Leitura desta ligada feita antes de o relógio acertar: calcula a hora pela diferença de millis()
    if (leitura.medida == 0 && relogioCerto() && inicio == leitura.inicio) {
        leitura.medida = (uint32_t) time(nullptr) - (millis() - leitura.ms) / 1000;
    }

    String topico = String("sala/") + SALA_ID + "/leitura";

    // Monta o JSON (sem "medida", o gravador usa a hora de chegada)
    String json = "{";
    json += "\"inicio\":\"" + String(leitura.inicio) + "\",";
    json += "\"seq\":" + String(leitura.seq) + ",";
    if (leitura.medida > 0) {
        json += "\"medida\":" + String(leitura.medida) + ",";
    }
    json += "\"temperatura\":" + String(leitura.temperatura, 2) + ",";
    json += "\"umidade\":" + String(leitura.umidade, 2);
    json += "}";

    Serial.print("Publicando em ");
    Serial.println(topico);
    Serial.println(json);

    // QoS 1: só devolve true depois que o broker confirmar.
    // Sem confirmação, a leitura continua na fila e é enviada de novo (mesmo seq);
    // se o broker já a tinha recebido, o gravador ignora a repetida pela chave
    return cliente.publish(topico, json, false, 1);
}
