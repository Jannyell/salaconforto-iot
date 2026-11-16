
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
// PUBLICA UMA LEITURA
// --------------------------------------

bool MqttPublicador::publicar(float temperatura, float umidade) {

    String topico = String("sala/") + SALA_ID + "/leitura";

    // Monta o JSON
    String json = "{";
    json += "\"inicio\":\"" + inicio + "\",";
    json += "\"seq\":" + String(seq) + ",";
    json += "\"temperatura\":" + String(temperatura, 2) + ",";
    json += "\"umidade\":" + String(umidade, 2);
    json += "}";

    Serial.print("Publicando em ");
    Serial.println(topico);
    Serial.println(json);

    // QoS 1: só devolve true depois que o broker confirmar
    bool sucesso = cliente.publish(topico, json, false, 1);

    // Sem confirmação em 5 s: reenvia a MESMA leitura (mesmo seq) uma vez.
    // Se o broker já tinha recebido e só a confirmação se perdeu, a leitura
    // chega repetida, e o gravador a ignora pela chave (sala, inicio, seq)
    if (!sucesso) {

        Serial.println("Sem confirmação do broker; reenviando a mesma leitura...");

        if (!cliente.connected()) {
            reconectar();
        }

        sucesso = cliente.connected() && cliente.publish(topico, json, false, 1);
    }

    // Depois do reenvio, o seq avança sempre: a próxima leitura nunca repete o número
    seq++;

    return sucesso;
}
