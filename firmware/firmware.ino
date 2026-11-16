#include "sensor.h"
#include "wificonector.h"
#include "mqttpublicador.h"
#include "credenciais.h"

// CONFIGURAÇÕES DO SENSOR
#define DHTPIN 17
#define DHTTYPE DHT22

// INSTÂNCIAS DOS MÓDULOS
Sensor sensor(DHTPIN, DHTTYPE);

WifiConector wifi;

MqttPublicador mqtt;

unsigned long ultimoEnvio = 0;


void setup() {

    Serial.begin(115200);

    // Inicializa o sensor
    sensor.iniciar();

    // Conecta ao Wi-Fi
    wifi.iniciar();

    // Conecta ao broker MQTT
    mqtt.iniciar();
}


void loop() {

    // Verifica a conexão Wi-Fi
    if (!wifi.conectado()) {

        Serial.println("Wi-Fi desconectado. Reconectando...");

        wifi.iniciar();
        return;
    }

    // Verifica a conexão com o broker
    if (!mqtt.conectado()) {

        mqtt.reconectar();
        delay(2000);
        return;
    }

    // Mantém a conexão com o broker viva (keepalive)
    mqtt.manter();

    // Ainda não chegou a hora da próxima medição
    if (millis() - ultimoEnvio < INTERVALO_ENVIO) {
        return;
    }

    ultimoEnvio = millis();

    float temperatura;
    float umidade;

    // Realiza a leitura do sensor
    if (sensor.ler(temperatura, umidade)) {

        Serial.println("\n--- NOVA LEITURA ---");

        Serial.print("Temperatura: ");
        Serial.print(temperatura);
        Serial.print(" °C | ");

        Serial.print("Umidade: ");
        Serial.print(umidade);
        Serial.println(" %");

        // Publica no broker (QoS 1)
        if (mqtt.publicar(temperatura, umidade)) {

            Serial.println("Leitura publicada (broker confirmou).");

        } else {

            Serial.println("Falha ao publicar a leitura.");
        }

    } else {

        Serial.println("Falha na leitura do sensor.");
    }
}
