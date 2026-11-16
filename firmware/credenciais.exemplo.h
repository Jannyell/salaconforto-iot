// Copie este arquivo para credenciais.h e preencha com os dados da sua rede.
// O credenciais.h fica fora do git (.gitignore).

#ifndef CREDENCIAIS_H
#define CREDENCIAIS_H

// Rede Wi-Fi da sala
#define WIFI_SSID "nome-da-rede"
#define WIFI_PASSWORD "senha-da-rede"

// Endereço do computador onde o Mosquitto roda (IP na rede local)
#define MQTT_HOST "192.168.0.10"
#define MQTT_PORTA 1883

// Sala desta placa (o simulador usa a sala 2)
#define SALA_ID "1"

// Intervalo entre as medições, em milissegundos
#define INTERVALO_ENVIO 20000

#endif
