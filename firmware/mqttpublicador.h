#ifndef MQTT_PUBLICADOR_H
#define MQTT_PUBLICADOR_H

#include <Arduino.h>

#include "fila.h"

class MqttPublicador {

public:
    void iniciar();

    bool conectado();

    bool reconectar();

    void manter();

    // Monta uma leitura nova (início desta ligada, próximo seq, hora da medida)
    Leitura novaLeitura(float temperatura, float umidade);

    // Publica com QoS 1; true só depois da confirmação do broker (PUBACK)
    bool publicar(Leitura &leitura);

private:
    String inicio;
    uint32_t seq = 0;
};

#endif
