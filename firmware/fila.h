#ifndef FILA_H
#define FILA_H

#include <Arduino.h>

// Até 180 leituras: 1 hora sem broker (ou sem Wi-Fi) no intervalo de 20 s.
// A fila fica na memória (RAM): se a placa reiniciar, ela se perde
#define FILA_MAX 180

// Uma leitura esperando para ser publicada
struct Leitura {
    char inicio[9];        // identificação da ligada da placa em que a leitura foi feita
    uint32_t seq;          // contador de leituras daquela ligada
    float temperatura;
    float umidade;
    uint32_t medida;       // hora da medida, em segundos desde 1970 (UTC); 0 = relógio ainda não acertado
    uint32_t ms;           // millis() no momento da medida, para calcular a hora depois
};

class FilaLeituras {

public:
    void adicionar(const Leitura &leitura);

    bool vazia();

    int tamanho();

    Leitura &primeira();

    void removerPrimeira();

private:
    Leitura itens[FILA_MAX];
    int posicao = 0;       // índice da leitura mais antiga
    int total = 0;
};

#endif
