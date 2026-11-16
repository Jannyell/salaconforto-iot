
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from services import armazenamento
from services import calculo


def registrar_leitura(sala, dados):

    # Verifica se os dados recebidos são um dicionário
    if not isinstance(dados, dict):
        return {"erro": "Dados inválidos"}, 400

    temperatura = dados.get("temperatura")
    umidade = dados.get("umidade")
    inicio = dados.get("inicio")
    seq = dados.get("seq")

    # Converte os valores para números
    try:
        temperatura = float(temperatura)
        umidade = float(umidade)
        seq = int(seq)

    except (ValueError, TypeError):
        return {"erro": "Valores numéricos são obrigatórios"}, 400

    # Verifica se os valores são válidos
    if not math.isfinite(temperatura) or not math.isfinite(umidade):
        return {"erro": "Valores numéricos inválidos"}, 400

    if not 0 <= umidade <= 100:
        return {"erro": "Umidade inválida"}, 400

    # Faixa que o DHT22 consegue medir
    if not -40 <= temperatura <= 80:
        return {"erro": "Temperatura fora da faixa do sensor"}, 400

    # Identificação da leitura: início do dispositivo + número de sequência
    # O seq precisa caber num inteiro do SQLite (64 bits)
    if not isinstance(inicio, str) or not 0 < len(inicio) <= 32 or not 0 <= seq < 2 ** 63:
        return {"erro": "Identificação da leitura inválida"}, 400

    # Calcula a sensação térmica
    sensacao = calculo.calcular_sensacao_termica(
        temperatura,
        umidade
    )

    # Monta a leitura
    leitura = {
        "sala": sala,
        "inicio": inicio,
        "seq": seq,
        "horario": datetime.now(ZoneInfo("America/Fortaleza")).isoformat(timespec="seconds"),
        "temperatura": temperatura,
        "umidade": umidade,
        "sensacao_termica": sensacao
    }

    # Salva no banco (a mesma leitura repetida é ignorada)
    if not armazenamento.salvar(leitura):
        return {"mensagem": "Leitura repetida", "dados": leitura}, 200

    return {
        "mensagem": "Leitura registrada",
        "dados": leitura
    }, 201


def obter_ultima_leitura(sala):

    leituras = armazenamento.listar(sala)

    if not leituras:
        return {"mensagem": "Nenhuma leitura disponível"}, 404

    return leituras[-1], 200


def listar_leituras(sala):

    return armazenamento.listar(sala), 200


def listar_salas():

    return armazenamento.salas(), 200
