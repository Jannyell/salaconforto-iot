#ifndef MQTT_PUBLICADOR_H
#define MQTT_PUBLICADOR_H

#include <Arduino.h>

class MqttPublicador {

public:
    void iniciar();

    bool conectado();

    bool reconectar();

    void manter();

    bool publicar(float temperatura, float umidade);

private:
    String inicio;
    unsigned long seq = 0;
};

#endif
