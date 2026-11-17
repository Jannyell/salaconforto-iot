#include "sensor.h"
#include "wificonector.h"
#include "mqttpublicador.h"
#include "fila.h"
#include "credenciais.h"

// CONFIGURAÇÕES DO SENSOR
#define DHTPIN 17
#define DHTTYPE DHT22

// INSTÂNCIAS DOS MÓDULOS
Sensor sensor(DHTPIN, DHTTYPE);

WifiConector wifi;

MqttPublicador mqtt;

FilaLeituras fila;

unsigned long ultimoEnvio = 0;
unsigned long ultimaTentativaWifi = 0;

// Tenta reconectar o Wi-Fi no máximo a cada 30 s (a tentativa bloqueia até 20 s)
#define INTERVALO_WIFI 30000


void setup() {

    Serial.begin(115200);

    // Inicializa o sensor
    sensor.iniciar();

    // Conecta ao Wi-Fi e acerta o relógio pela internet (NTP, em UTC)
    wifi.iniciar();
    configTime(0, 0, "pool.ntp.org", "time.google.com");

    // Conecta ao broker MQTT
    mqtt.iniciar();
}


void loop() {

    // 1. Mede no intervalo, com ou sem rede: a leitura vai para a fila
    if (millis() - ultimoEnvio >= INTERVALO_ENVIO) {

        ultimoEnvio = millis();
        medir();
    }

    // 2. Sem Wi-Fi: as leituras ficam na fila
    if (!wifi.conectado()) {

        if (millis() - ultimaTentativaWifi >= INTERVALO_WIFI) {

            Serial.println("Wi-Fi desconectado. Reconectando...");

            ultimaTentativaWifi = millis();
            wifi.iniciar();
        }
        return;
    }

    // 3. Sem broker: as leituras ficam na fila
    if (!mqtt.conectado()) {

        mqtt.reconectar();
        delay(2000);
        return;
    }

    // Mantém a conexão com o broker viva (keepalive)
    mqtt.manter();

    // 4. Publica a fila, da mais antiga para a mais nova; para na primeira sem confirmação
    while (!fila.vazia()) {

        if (!mqtt.publicar(fila.primeira())) {

            Serial.println("Sem confirmação do broker: a leitura continua na fila.");
            break;
        }

        fila.removerPrimeira();

        Serial.print("Leitura publicada (broker confirmou). Na fila: ");
        Serial.println(fila.tamanho());
    }
}


// --------------------------------------
// MEDE E GUARDA NA FILA
// --------------------------------------

void medir() {

    float temperatura;
    float umidade;

    // Realiza a leitura do sensor
    if (!sensor.ler(temperatura, umidade)) {

        Serial.println("Falha na leitura do sensor.");
        return;
    }

    Serial.println("\n--- NOVA LEITURA ---");

    Serial.print("Temperatura: ");
    Serial.print(temperatura);
    Serial.print(" °C | ");

    Serial.print("Umidade: ");
    Serial.print(umidade);
    Serial.println(" %");

    fila.adicionar(mqtt.novaLeitura(temperatura, umidade));
}
