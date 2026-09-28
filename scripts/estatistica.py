"""Engine estatistica v0 do Radar ENEM.

Funcoes puras sobre as faixas de nota da camada ANALYTICS
(data/analytics/dist_notas.parquet). O ETL usa `faixas` para gerar o
artefato; o app usa `percentil_faixas` e `histograma` para responder ao
usuario sem tocar no dado individual.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from colunas import PISO_GRUPO  # noqa: E402

Faixa = tuple[float, float, int]


def faixas(contagens: list[tuple[float, int]], piso: int = PISO_GRUPO) -> list[Faixa]:
    """Junta notas consecutivas ate cada faixa ter pelo menos `piso` pessoas.

    `contagens` e (nota, n) em ordem crescente de nota. Devolve
    (nota_min, nota_max, n). A sobra final abaixo do piso entra na ultima
    faixa; se o total nao chega ao piso, nada e publicado.
    """
    saida: list[Faixa] = []
    inicio, acumulado = None, 0
    for nota, n in contagens:
        if inicio is None:
            inicio = nota
        acumulado += n
        if acumulado >= piso:
            saida.append((inicio, nota, acumulado))
            inicio, acumulado = None, 0
    if acumulado and saida:
        nota_min, _, n = saida[-1]
        saida[-1] = (nota_min, contagens[-1][0], n + acumulado)
    return saida


def percentil_faixas(faixas_area: list[Faixa], nota: float) -> float:
    """Percentil de posicao de `nota` (0 a 100) a partir das faixas.

    Mesma convencao do percentil exato (empate conta pela metade). Dentro de
    uma faixa com varias notas a posicao e interpolada; o erro fica limitado
    ao peso da faixa (n da faixa / total).
    """
    total = sum(n for _, _, n in faixas_area)
    abaixo = 0.0
    for nota_min, nota_max, n in faixas_area:
        if nota_max < nota:
            abaixo += n
        elif nota_min <= nota:
            fracao = 0.5 if nota_min == nota_max else (nota - nota_min) / (nota_max - nota_min)
            abaixo += n * fracao
            break
        else:
            break
    return abaixo / total * 100


def histograma(faixas_area: list[Faixa], largura: float = 20) -> list[tuple[float, float]]:
    """Reagrupa as faixas em classes de `largura` pontos: (inicio, % do total).

    Cada faixa vai inteira para a classe do seu ponto medio. Como toda faixa
    ja tem ao menos PISO_GRUPO pessoas, toda classe tambem tem.
    """
    total = sum(n for *_, n in faixas_area)
    classes: dict[float, int] = {}
    for nota_min, nota_max, n in faixas_area:
        inicio = (nota_min + nota_max) / 2 // largura * largura
        classes[inicio] = classes.get(inicio, 0) + n
    return [(inicio, n / total * 100) for inicio, n in sorted(classes.items())]
