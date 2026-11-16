
#include "wificonector.h"

#include <WiFi.h>

#include "credenciais.h"

// --------------------------------------
// INICIA A CONEXÃO WI-FI
// --------------------------------------

void WifiConector::iniciar() {

    Serial.println("Conectando ao Wi-Fi...");

    // Define o ESP32 como dispositivo cliente
    WiFi.mode(WIFI_STA);

    // Limpa uma possível configuração anterior
    WiFi.disconnect(true);

    delay(1000);

    // Habilita a reconexão automática
    WiFi.setAutoReconnect(true);

    // Inicia a conexão
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int tentativas = 0;

    // Aguarda a conexão por até 20 segundos
    while (!conectado() && tentativas < 40) {

        delay(500);

        Serial.print(".");

        tentativas++;
    }

    if (conectado()) {

        Serial.println("\nWi-Fi conectado!");

        Serial.print("IP do ESP32: ");
        Serial.println(WiFi.localIP());

        Serial.print("Intensidade do sinal: ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");

    } else {

        Serial.println("\nFalha ao conectar ao Wi-Fi.");
    }
}

// --------------------------------------
// VERIFICA A CONEXÃO
// --------------------------------------

bool WifiConector::conectado() {

    return WiFi.status() == WL_CONNECTED;
}
