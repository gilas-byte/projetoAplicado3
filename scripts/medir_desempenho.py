#!/usr/bin/env python3
"""Mede o desempenho do lado do servidor com os artefatos reais (RNF02).

Mede o que depende do código e dos dados, no ambiente em que roda (notebook da
equipe ou Shell do Replit):

1. carga de cada artefato pela mesma função que a página usa (uma vez por
   processo, depois fica no cache do Streamlit);
2. tempo de uma consulta de cada página (validar a entrada e calcular a
   comparação), em N consultas sorteadas com entradas válidas: p50, p95 e máximo;
3. pico de memória do processo (onde o sistema informa).

Não mede a rede nem o desenho no navegador: para o tempo ponta a ponta, ver
scripts/checar_saude.py e a medição manual descrita em docs/deploy/replit.md.

A saída vai para docs/deploy/medicoes/<ambiente>-<data>.json. Só tem tempos,
tamanhos e a descrição da máquina; nenhuma nota digitada nem contagem de grupo.

Uso:
  python scripts/medir_desempenho.py --ambiente local
  python scripts/medir_desempenho.py --ambiente replit --consultas 300
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import capital_escolar  # noqa: E402
import equidade  # noqa: E402
import territorial  # noqa: E402
from estatistica import percentil_exato_acumulado, resumo  # noqa: E402

ANALYTICS = RAIZ / "data" / "analytics"
SAIDA = RAIZ / "docs" / "deploy" / "medicoes"
ALTERNATIVAS_Q006 = "ABCDEFGHIJKLMNOPQ"
ALTERNATIVAS_PAIS = "ABCDEFGH"


def cronometrar(funcao, *args, **kwargs):
    inicio = time.perf_counter()
    resultado = funcao(*args, **kwargs)
    return resultado, (time.perf_counter() - inicio) * 1000


def percentis(tempos: list[float]) -> dict:
    ordenados = sorted(tempos)

    def p(q: float) -> float:
        return ordenados[min(len(ordenados) - 1, int(q * len(ordenados)))]

    return {"consultas": len(ordenados), "p50_ms": round(p(0.50), 2), "p95_ms": round(p(0.95), 2),
            "max_ms": round(ordenados[-1], 2)}


def nota_aleatoria(gerador: random.Random, area: str) -> float:
    if area == "redacao":
        return float(gerador.randrange(0, 1001, 20))
    return round(gerador.uniform(300, 850), 1)


def carregar_nacional():
    linhas = duckdb.execute(
        "SELECT ano, area, nota, n, abaixo FROM read_parquet(?) ORDER BY ano, area, nota",
        [str(ANALYTICS / "dist_exata.parquet")],
    ).fetchall()
    cdfs = {}
    for ano, area, nota, n, abaixo in linhas:
        cdfs.setdefault((ano, area), []).append((float(nota), int(n), int(abaixo)))
    return cdfs


def memoria_pico_mb() -> float | None:
    try:
        import resource
    except ImportError:  # Windows
        return None
    pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(pico / 1024 if sys.platform != "darwin" else pico / 1024 / 1024, 1)


def commit_atual() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ambiente", required=True, help="rotulo do ambiente, ex.: local ou replit")
    parser.add_argument("--consultas", type=int, default=200, help="consultas sorteadas por pagina")
    parser.add_argument("--semente", type=int, default=2026)
    args = parser.parse_args()
    gerador = random.Random(args.semente)

    cargas = {}
    nacional, cargas["inicio (dist_exata)"] = cronometrar(carregar_nacional)
    cdf_eq, cargas["equidade"] = cronometrar(equidade.carregar, ANALYTICS / "dist_equidade.parquet")
    cdf_te, cargas["territorial"] = cronometrar(territorial.carregar, ANALYTICS / "dist_territorial.parquet")
    cdf_ca, cargas["capital"] = cronometrar(capital_escolar.carregar, ANALYTICS / "dist_capital.parquet")

    anos = sorted({ano for ano, _ in nacional})
    areas = ("cn", "ch", "lc", "mt", "redacao")
    tempos = {"inicio": [], "equidade": [], "territorial": [], "capital": []}
    for _ in range(args.consultas):
        ano, area = gerador.choice(anos), gerador.choice(areas)
        nota = nota_aleatoria(gerador, area)

        def inicio():
            cdf = nacional[(ano, area)]
            return percentil_exato_acumulado(cdf, nota), resumo(cdf)

        tempos["inicio"].append(cronometrar(inicio)[1])
        entrada = equidade.validar_entrada(ano, area, nota, gerador.choice(ALTERNATIVAS_Q006), anos)
        tempos["equidade"].append(cronometrar(equidade.comparar, cdf_eq, entrada)[1])
        entrada = territorial.validar_entrada(ano, area, nota, gerador.choice(territorial.UFS), anos)
        tempos["territorial"].append(cronometrar(territorial.comparar, cdf_te, entrada)[1])
        entrada = capital_escolar.validar_entrada(ano, area, nota, gerador.choice(ALTERNATIVAS_PAIS),
                                                  gerador.choice(ALTERNATIVAS_PAIS), anos)
        tempos["capital"].append(cronometrar(capital_escolar.comparar, cdf_ca, entrada,
                                             comparar_outro_nivel=True)[1])

    resultado = {
        "ambiente": args.ambiente,
        "medido_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versao_codigo_git": commit_atual(),
        "maquina": {"sistema": platform.platform(), "python": platform.python_version(),
                    "cpus_visiveis": os.cpu_count(), "duckdb": duckdb.__version__},
        "carga_ms": {k: round(v, 1) for k, v in cargas.items()},
        "consulta": {k: percentis(v) for k, v in tempos.items()},
        "memoria_pico_mb": memoria_pico_mb(),
        "meta_rnf02_ms": 3000,
    }
    SAIDA.mkdir(parents=True, exist_ok=True)
    arquivo = SAIDA / f"{args.ambiente}-{datetime.now().strftime('%Y-%m-%d')}.json"
    arquivo.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: resultado[k] for k in ("carga_ms", "consulta", "memoria_pico_mb")},
                     ensure_ascii=False, indent=2))
    print(f"Gravado em {arquivo.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
