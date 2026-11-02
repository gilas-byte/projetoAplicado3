"""Engine estatistica v0 do Radar ENEM.

Funcoes puras sobre as faixas de nota da camada ANALYTICS
(data/analytics/dist_notas.parquet). O ETL usa `faixas` para gerar o
artefato; o app usa `percentil_faixas` e `histograma` para responder ao
usuario sem tocar no dado individual.

As medidas do motor v1 (`resumo`, `quantil`, `z_score` e
`prob_superioridade`) usam a CDF exata de data/analytics/dist_exata.parquet.
"""

from __future__ import annotations

import sys
from bisect import bisect_left
from fractions import Fraction
from math import isfinite, sqrt
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


# ===================================================== CDF EMPIRICA EXATA

def percentil_exato_acumulado(
    distribuicao: list[tuple[float, int, int]], nota: float
) -> float:
    """Percentil empírico exato de uma nota com empates por posto médio.

    `distribuicao`: (nota_observada, frequencia, quantidade_abaixo),
    em ordem estritamente crescente; frequência positiva. Não faz
    interpolação, mesmo quando a nota consultada está entre duas notas.
    Pré-condições de integridade são validadas na geração do ETL e por testes.

    O resultado cobre TODA a população elegível desse (ano, área), não
    autoriza recortes socioeconômicos arbitrários nem inferência causal.
    """
    if not distribuicao:
        raise ValueError('distribuicao vazia: grupo insuficiente')
    if not isfinite(nota):
        raise ValueError('nota consultada precisa ser finita')
    notas = [item[0] for item in distribuicao]
    pos = bisect_left(notas, nota)
    ultima = distribuicao[-1]
    total = ultima[2] + ultima[1]
    if total <= 0:
        raise ValueError('distribuicao sem participantes validos')
    if pos >= len(distribuicao):
        return 100.0
    valor, n, abaixo = distribuicao[pos]
    iguais = n if valor == nota else 0
    return (abaixo + iguais / 2) / total * 100


def construir_acumulada(contagens: list[tuple[float, int]]) -> list[tuple[float, int, int]]:
    """Converte distribuição de frequências ordenadas em CDF exata.

    Evita ambiguidades com duplicação de nota, pesos negativos e não finitos.
    Pode ser utilizada diretamente em fixtures independentes de DuckDB.
    """
    resultado = []
    abaixo = 0
    anterior = float('-inf')
    for nota, n in contagens:
        if not isfinite(nota) or nota <= anterior or not isinstance(n, int) or n <= 0:
            raise ValueError('frequencias precisam ter notas finitas crescentes e n positivo')
        resultado.append((float(nota), n, abaixo))
        abaixo += n
        anterior = nota
    return resultado


# ===================================================== MEDIDAS DO MOTOR V1

def _total(distribuicao: list[tuple[float, int, int]]) -> int:
    """Total de participantes da distribuição (nota, n, abaixo)."""
    if not distribuicao:
        raise ValueError('distribuicao vazia: grupo insuficiente')
    _, n, abaixo = distribuicao[-1]
    return abaixo + n


def quantil(distribuicao: list[tuple[float, int, int]], p: float) -> float:
    """Menor nota observada em que `abaixo + n >= p * N`, para 0 <= p <= 1.

    `p` entra pelo valor decimal: p * N em ponto flutuante daria 7,000...1
    para p = 0.07 e N = 100, e o quantil pularia para a nota seguinte.
    """
    total = _total(distribuicao)
    if not 0 <= p <= 1:
        raise ValueError('p precisa estar entre 0 e 1')
    alvo = Fraction(str(p)) * total
    return next(nota for nota, n, abaixo in distribuicao if abaixo + n >= alvo)


def resumo(distribuicao: list[tuple[float, int, int]]) -> dict:
    """N, média, variância populacional, desvio-padrão e mediana.

    As somas usam frações: uma distribuição de nota única dá variância
    exatamente 0, sem resíduo de ponto flutuante.
    """
    total = _total(distribuicao)
    media = sum(n * Fraction(nota) for nota, n, _ in distribuicao) / total
    variancia = sum(n * (Fraction(nota) - media) ** 2 for nota, n, _ in distribuicao) / total
    return {
        'N': total,
        'media': float(media),
        'variancia': float(variancia),
        'desvio': sqrt(variancia),
        'mediana': quantil(distribuicao, 0.5),
    }


def z_score(distribuicao: list[tuple[float, int, int]], nota: float) -> float:
    """Distância de `nota` à média do grupo, em desvios-padrão."""
    if not isfinite(nota):
        raise ValueError('nota consultada precisa ser finita')
    medidas = resumo(distribuicao)
    if medidas['desvio'] == 0:
        raise ValueError('desvio-padrao zero: z-score indefinido')
    return (nota - medidas['media']) / medidas['desvio']


def prob_superioridade(
    dist_a: list[tuple[float, int, int]], dist_b: list[tuple[float, int, int]]
) -> float:
    """P(A > B) + 0,5 * P(A = B), exata; equivale a U / (n_A * n_B)."""
    total_a, total_b = _total(dist_a), _total(dist_b)
    notas_b = [item[0] for item in dist_b]
    dobro_de_u = 0  # inteiro: empate vale 1 e a soma não perde precisão
    for nota, n, _ in dist_a:
        pos = bisect_left(notas_b, nota)
        if pos == len(dist_b):
            dobro_de_u += n * 2 * total_b
            continue
        valor, iguais, abaixo = dist_b[pos]
        dobro_de_u += n * (2 * abaixo + (iguais if valor == nota else 0))
    return dobro_de_u / (2 * total_a * total_b)
