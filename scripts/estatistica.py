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


# ====================================== EXIBIÇÃO PROTEGIDA (DL-01; DL-04, item 8)
#
# Funções compartilhadas pelos módulos autorais (Equidade, Recorte territorial e
# Capital escolar familiar). Cada módulo importa daqui, sem importar o outro: a
# lógica de cada módulo fica no próprio arquivo e o que é comum fica neste
# (observação de autoria da AV4 no Plano de Trabalho; review da DL-05, item 13).


def limites_exibicao(total: int, piso: int = PISO_GRUPO) -> tuple[int, int]:
    """(inferior, superior) do percentil exibível, em décimos de ponto percentual.

    superior = 100 · (N − piso) / N arredondado para baixo; inferior =
    100 · piso / N arredondado para cima, ambos com uma casa decimal. Conta em
    inteiros: nenhum erro de ponto flutuante desloca a borda. Com N < 2 · piso
    os limites se cruzam (inferior > superior) e nenhuma posição sai exata.
    """
    if total <= 0:
        raise ValueError("grupo vazio")
    superior = 1000 * (total - piso) // total
    inferior = -(-1000 * piso // total)
    return inferior, superior


def alcance_do_limite(total: int, lado: str, piso: int = PISO_GRUPO) -> float:
    """Até quantas pessoas da ponta (empatados pela metade) a posição fica em limite.

    Pela regra do item 8.2: em "acima de X%", p > X equivale a
    acima + metade dos empatados < N · (1000 − superior) / 1000; em "abaixo de",
    abaixo + metade < N · inferior / 1000. Nunca menos que `piso`; nos grupos
    grandes, cerca de 0,1% de N por causa do arredondamento.
    """
    inferior, superior = limites_exibicao(total, piso)
    if lado == "acima":
        return total * (1000 - superior) / 1000
    if lado == "abaixo":
        return total * inferior / 1000
    raise ValueError(f"lado inválido: {lado!r}")


def dobro_posicao(cdf: list[tuple[float, int, int]], nota: float) -> tuple[int, int]:
    """(2 · abaixo + iguais, N): o percentil exato é 100 · a / (2N), sem arredondar.

    Fonte única da posição na exibição (percentil, texto e limite). Mesmas
    regras de percentil_exato_acumulado, conferidas em teste.
    """
    if not cdf:
        raise ValueError("distribuicao vazia: grupo insuficiente")
    if not isfinite(nota):
        raise ValueError("nota consultada precisa ser finita")
    total = cdf[-1][1] + cdf[-1][2]
    pos = bisect_left([item[0] for item in cdf], nota)
    if pos == len(cdf):
        return 2 * total, total
    valor, n, abaixo = cdf[pos]
    return 2 * abaixo + (n if valor == nota else 0), total


def exibir_percentil(cdf: list[tuple[float, int, int]], nota: float,
                     piso: int = PISO_GRUPO) -> tuple[str, bool]:
    """Texto do percentil para a interface e se ele está em limite.

    Compara o percentil exato com o limite já arredondado (DL-04, 8.5): assim
    "acima de X%" só aparece quando p > X de fato e a ordem das posições
    exibidas nunca se inverte. Em limite: "acima de X%" ou "abaixo de X%".
    """
    dobro, total = dobro_posicao(cdf, nota)
    return texto_da_posicao(dobro, total, piso)


def texto_da_posicao(dobro: int, total: int, piso: int = PISO_GRUPO) -> tuple[str, bool]:
    """Mesma regra de exibir_percentil a partir de (2 · abaixo + iguais, N).

    Separada para a auditoria (scripts/auditoria_limites.py) varrer milhões de
    notas sem refazer a busca na CDF.
    """
    inferior, superior = limites_exibicao(total, piso)
    # p em décimos = 1000 · dobro / (2N); compara multiplicando em inteiros.
    if 1000 * dobro > superior * 2 * total:
        return f"acima de {formatar_decimos(superior)}", True
    if 1000 * dobro < inferior * 2 * total:
        return f"abaixo de {formatar_decimos(inferior)}", True
    return formatar_percentil(dobro * 100 / (2 * total)), False


def densidade_protegida(cdf: list[tuple[float, int, int]], piso: int = PISO_GRUPO,
                        largura_min: float = 10.0) -> list[tuple[float, float, float]]:
    """Histograma de largura variável do grupo: [(início, fim, % do grupo por 10 pontos)].

    Parte das faixas do motor (cada uma com pelo menos `piso` pessoas), então
    o gráfico não revela a frequência de nenhuma nota isolada. Faixas
    vizinhas são somadas até a barra cobrir `largura_min` pontos: em grupos
    grandes uma faixa pode ter só 0,1 ponto de largura. Cada barra vai do
    início da sua primeira faixa ao início da faixa seguinte, e a altura é a
    densidade, para que barras largas (grupos pequenos) não virem picos. A
    área total é 100%.
    """
    blocos = faixas([(nota, n) for nota, n, _ in cdf], piso)
    if not blocos:
        return []
    total = sum(n for *_, n in blocos)
    fins = [b[0] for b in blocos[1:]] + [blocos[-1][1]]
    saida, inicio, acumulado = [], None, 0
    for i, (comeco, _, n) in enumerate(blocos):
        if inicio is None:
            inicio = comeco
        acumulado += n
        ultimo = i == len(blocos) - 1
        if fins[i] - inicio >= largura_min or ultimo:
            fim = max(fins[i], inicio + 1.0) if ultimo else fins[i]
            saida.append((inicio, fim, acumulado / total * 100 / (fim - inicio) * 10))
            inicio, acumulado = None, 0
    return saida


def formatar_percentil(p: float) -> str:
    return f"{p:.1f}".replace(".", ",") + "%"


def formatar_decimos(decimos: int) -> str:
    return f"{decimos // 10},{decimos % 10}%"
