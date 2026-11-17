#!/usr/bin/env python3
"""Confere se o app publicado responde e mede o tempo de resposta pela rede.

Faz N requisições ao endpoint de saúde do Streamlit (/_stcore/health) e à
página inicial, com um intervalo entre elas, e informa o status HTTP e os tempos
p50, p95 e máximo. Serve para três coisas da AV6:

- evidência de que o link público está no ar (validação da aplicação em nuvem);
- tempo de resposta pela rede, que scripts/medir_desempenho.py não mede;
- monitoramento simples: rodar de tempos em tempos ou apontar um serviço externo de
  disponibilidade (UptimeRobot, por exemplo) para a mesma URL de saúde;
- conferência de privacidade: tenta baixar os artefatos por caminhos óbvios (inclusive
  pelo servidor de arquivos estáticos, com "..") e falha se algum responder com um
  arquivo Parquet (ADR-001: a CDF exata nunca pode ser servida).

Mede só o primeiro carregamento HTTP: o resultado de uma consulta chega depois,
pela conexão WebSocket do Streamlit, e é medido à parte (docs/deploy/replit.md).
Nenhum dado é enviado ao app.

Uso:
  python scripts/checar_saude.py https://radar-enem.replit.app
  python scripts/checar_saude.py https://radar-enem.replit.app --vezes 30 --intervalo 2 --gravar
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "docs" / "deploy" / "medicoes"


def requisitar(url: str, tempo_limite: float) -> tuple[int | None, float]:
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "radar-enem-saude"}),
                                    timeout=tempo_limite) as resposta:
            resposta.read()
            status = resposta.status
    except urllib.error.HTTPError as erro:
        status = erro.code
    except (urllib.error.URLError, TimeoutError, OSError):
        status = None
    return status, (time.perf_counter() - inicio) * 1000


ARTEFATOS = ("dist_notas", "dist_exata", "dist_equidade", "dist_territorial", "dist_capital")
CAMINHOS_SONDADOS = (
    "/data/analytics/{a}.parquet",
    "/app/static/../../data/analytics/{a}.parquet",
    "/app/static/%2e%2e/%2e%2e/data/analytics/{a}.parquet",
    "/app/static/..%2F..%2Fdata%2Fanalytics%2F{a}.parquet",
    "/{a}.parquet",
)


def artefatos_expostos(base: str, tempo_limite: float) -> list[str]:
    """Caminhos que devolveram um Parquet (assinatura PAR1). Deve ser lista vazia.

    O Streamlit responde 200 com a própria página para caminhos desconhecidos, então o
    status não basta: o que importa é o conteúdo não ser um Parquet.
    """
    expostos = []
    for modelo in CAMINHOS_SONDADOS:
        for artefato in ARTEFATOS:
            caminho = modelo.format(a=artefato)
            try:
                with urllib.request.urlopen(urllib.request.Request(base + caminho), timeout=tempo_limite) as r:
                    if r.read(4) == b"PAR1":
                        expostos.append(caminho)
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
    return expostos


def resumir(medidas: list[tuple[int | None, float]]) -> dict:
    tempos = sorted(t for s, t in medidas if s == 200)
    falhas = sum(1 for s, _ in medidas if s != 200)
    saida = {"requisicoes": len(medidas), "falhas": falhas}
    if tempos:
        p = lambda q: tempos[min(len(tempos) - 1, int(q * len(tempos)))]  # noqa: E731
        saida.update(p50_ms=round(p(0.5), 1), p95_ms=round(p(0.95), 1), max_ms=round(tempos[-1], 1))
    return saida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="endereco publico do app, sem barra no fim")
    parser.add_argument("--vezes", type=int, default=20)
    parser.add_argument("--intervalo", type=float, default=1.0, help="segundos entre requisicoes")
    parser.add_argument("--tempo-limite", type=float, default=30.0)
    parser.add_argument("--gravar", action="store_true", help="grava em docs/deploy/medicoes/")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    saude, pagina = [], []
    for i in range(args.vezes):
        saude.append(requisitar(f"{base}/_stcore/health", args.tempo_limite))
        pagina.append(requisitar(f"{base}/", args.tempo_limite))
        if i < args.vezes - 1:
            time.sleep(args.intervalo)

    resultado = {
        "url": base,
        "medido_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "primeira_requisicao_ms": round(saude[0][1], 1),
        "saude": resumir(saude),
        "pagina_inicial": resumir(pagina),
        "artefatos_expostos": artefatos_expostos(base, args.tempo_limite),
    }
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    if args.gravar:
        SAIDA.mkdir(parents=True, exist_ok=True)
        arquivo = SAIDA / f"saude-{datetime.now().strftime('%Y-%m-%d-%H%M')}.json"
        arquivo.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Gravado em {arquivo.relative_to(RAIZ)}")
    if resultado["artefatos_expostos"]:
        print("FALHA DE PRIVACIDADE: artefato servido em " + ", ".join(resultado["artefatos_expostos"]))
        return 2
    return 0 if resultado["saude"]["falhas"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
