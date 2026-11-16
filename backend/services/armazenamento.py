
import sqlite3

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


# --------------------------------------
# CONFIGURAÇÕES
# --------------------------------------

FUSO_HORARIO = ZoneInfo("America/Fortaleza")

ARQUIVO = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "medicoes.db"
)


# --------------------------------------
# CONEXÃO
# --------------------------------------

def conectar():

    ARQUIVO.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conexao = sqlite3.connect(ARQUIVO, timeout=10)
    conexao.row_factory = sqlite3.Row

    # WAL: um escritor por vez e vários leitores ao mesmo tempo
    conexao.execute("PRAGMA journal_mode=WAL")

    return conexao


# --------------------------------------
# INICIALIZAÇÃO
# --------------------------------------

def inicializar():

    with conectar() as conexao:

        # A chave (sala, inicio, seq) identifica cada leitura:
        # se a mesma leitura chegar duas vezes, a segunda é ignorada
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS leituras (
                sala TEXT NOT NULL,
                inicio TEXT NOT NULL,
                seq INTEGER NOT NULL,
                horario TEXT NOT NULL,
                temperatura REAL NOT NULL,
                umidade REAL NOT NULL,
                sensacao_termica REAL NOT NULL,
                PRIMARY KEY (sala, inicio, seq)
            )
        """)


# --------------------------------------
# SALVAR MEDIÇÃO
# --------------------------------------

def salvar(medicao):
    """
    Grava a leitura. Devolve True se ela foi gravada
    e False se já existia (leitura repetida).
    """

    inicializar()

    with conectar() as conexao:

        cursor = conexao.execute(
            """
            INSERT OR IGNORE INTO leituras
                (sala, inicio, seq, horario, temperatura, umidade, sensacao_termica)
            VALUES
                (:sala, :inicio, :seq, :horario, :temperatura, :umidade, :sensacao_termica)
            """,
            medicao
        )

        return cursor.rowcount == 1


# --------------------------------------
# LISTAR MEDIÇÕES DE HOJE
# --------------------------------------

def listar(sala):

    inicializar()

    # Obtém a data atual de Fortaleza
    hoje = datetime.now(FUSO_HORARIO).date().isoformat()

    with conectar() as conexao:

        linhas = conexao.execute(
            """
            SELECT horario, temperatura, umidade, sensacao_termica
            FROM leituras
            WHERE sala = ? AND horario LIKE ?
            ORDER BY horario
            """,
            (sala, f"{hoje}%")
        ).fetchall()

    return [dict(linha) for linha in linhas]


# --------------------------------------
# LISTAR SALAS
# --------------------------------------

def salas():

    inicializar()

    with conectar() as conexao:

        linhas = conexao.execute(
            "SELECT DISTINCT sala FROM leituras ORDER BY sala"
        ).fetchall()

    return [linha["sala"] for linha in linhas]
