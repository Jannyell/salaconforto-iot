
from datetime import datetime

from flask import request, jsonify

import services.leitura_service as service


def log(mensagem):
    print(f"[api {datetime.now():%H:%M:%S}] {mensagem}", flush=True)


def configurar_rotas(app):

    @app.route("/", methods=["GET"])
    def inicio():
        return jsonify({"mensagem": "API SalaConforto funcionando!"}), 200

    # A API só lê o banco: quem grava é o gravador (backend/gravador.py)

    @app.route("/api/salas", methods=["GET"])
    def todas_salas():
        resultado, status = service.listar_salas()
        log(f"GET /api/salas → {len(resultado)} sala(s)")
        return jsonify(resultado), status

    @app.route("/api/leituras/ultima", methods=["GET"])
    def ultima_leitura():
        sala = request.args.get("sala", "1")
        resultado, status = service.obter_ultima_leitura(sala)
        log(f"GET /api/leituras/ultima?sala={sala} → {status}")
        return jsonify(resultado), status

    @app.route("/api/leituras", methods=["GET"])
    def todas_leituras():
        sala = request.args.get("sala", "1")
        resultado, status = service.listar_leituras(sala)
        log(f"GET /api/leituras?sala={sala} → {len(resultado)} leitura(s) de hoje")
        return jsonify(resultado), status
