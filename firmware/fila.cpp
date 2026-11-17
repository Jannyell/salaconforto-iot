#include "fila.h"

// --------------------------------------
// ADICIONA E REMOVE LEITURAS (lista circular)
// --------------------------------------

void FilaLeituras::adicionar(const Leitura &leitura) {

    // Fila cheia: descarta a mais antiga para guardar a nova
    if (total == FILA_MAX) {

        Serial.println("Fila cheia: a leitura mais antiga foi descartada.");

        posicao = (posicao + 1) % FILA_MAX;
        total--;
    }

    itens[(posicao + total) % FILA_MAX] = leitura;
    total++;
}

void FilaLeituras::removerPrimeira() {

    if (total == 0) {
        return;
    }

    posicao = (posicao + 1) % FILA_MAX;
    total--;
}

bool FilaLeituras::vazia() {

    return total == 0;
}

int FilaLeituras::tamanho() {

    return total;
}

Leitura &FilaLeituras::primeira() {

    return itens[posicao];
}
