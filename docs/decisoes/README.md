# Decision Log — Radar ENEM

Registro das decisões de produto, metodologia e equipe. Decisões de
arquitetura com análise de alternativas ficam em ADRs (`docs/av3/DECISAO-*.md`);
este log guarda a decisão em si, quem decidiu, quando e onde ela aparece no
código.

Cada entrada tem: data, responsável pela decisão, situação (proposta, aceita,
substituída), contexto, decisão e evidência no repositório. Uma decisão nunca é
apagada: quando muda, a entrada antiga recebe "substituída por DL-xx".

| ID | Data | Assunto | Responsável | Situação |
| --- | --- | --- | --- | --- |
| [DL-01](#dl-01--convenções-estatísticas-do-motor-v1) | 02/11/2026 | Convenções estatísticas do motor v1 | Samuel (PO) | Aceita |
| [DL-02](#dl-02--saída-de-guilherme-zamboni-e-redistribuição-dos-módulos) | 02/11/2026 | Saída de Guilherme Zamboni e redistribuição dos módulos | Samuel (PO) | Aceita |
| [DL-03](#dl-03--regras-do-módulo-equidade-socioeconômica) | 02/11/2026 | Regras do módulo Equidade socioeconômica | Samuel (autor do módulo) | Aceita |

---

## DL-01 — Convenções estatísticas do motor v1

- **Data:** 02/11/2026
- **Responsável:** Samuel Silva de Rezende (Product Owner, aprova regras do motor pela matriz RACI do Plano AV1)
- **Situação:** aceita
- **Contexto:** o contrato do motor estatístico v1 (Vinícius, 01/11/2026) deixou
  três convenções pendentes de aceite: tipo de variância, definição da mediana e
  casas decimais exibidas.
- **Decisão:**
  1. **Variância populacional** (divisor N, `ddof = 0`). Cada edição do ENEM é o
     conjunto completo dos participantes elegíveis, não uma amostra. Com o piso
     de 100 participantes por grupo, a diferença para o divisor N − 1 é de no
     máximo 0,5% do desvio-padrão.
  2. **Mediana = `quantil(distribuicao, 0.5)`**, ou seja, a menor nota observada
     em que `abaixo + n ≥ 0,5 · N` (mediana inferior). Com N par e as duas notas
     centrais diferentes, a mediana é a nota de baixo, e não a média das duas.
     Assim a mediana é sempre uma nota que algum participante realmente obteve e
     segue a mesma regra de todos os quantis do motor. Quem comparar com
     `numpy.median` deve esperar essa diferença.
  3. **Arredondamento só na exibição.** As funções do motor não arredondam.
     Na interface: percentil com 1 casa decimal (já é o padrão do app desde o
     MVP), notas, média e mediana com 1 casa, Z-Score com 2 casas, probabilidade
     de superioridade em porcentagem com 1 casa.
- **Evidência:** `scripts/estatistica.py` (`resumo`, `quantil`),
  `tests/test_motor.py::TestQuantil::test_mediana_com_n_par_e_a_nota_inferior`,
  `scripts/equidade.py` (`formatar_*`).

## DL-02 — Saída de Guilherme Zamboni e redistribuição dos módulos

- **Data do registro:** 02/11/2026 (a saída já constava no roteiro da AV2, 28/09/2026)
- **Responsável:** Samuel Silva de Rezende (Product Owner)
- **Situação:** aceita
- **Contexto:** o Plano de Trabalho AV1 previu quatro integrantes e quatro
  módulos comparativos. Guilherme Zamboni deixou a equipe antes da AV2 e a
  mudança só estava registrada em `docs/apresentacao/AV2.md`.
- **Decisão:**
  - A equipe passa a ter três integrantes: Samuel Silva de Rezende (Líder /
    Product Owner), Vinícius Joacir dos Anjos (Desenvolvimento e IA) e Guilherme
    da Silva Anselmo (QA, segurança, design e frontend).
  - Os quatro módulos são mantidos. Guilherme Anselmo assume, além de Capital
    escolar familiar, o módulo **Rede de ensino de origem**, que era do
    integrante que saiu.
  - Distribuição final: Equidade socioeconômica (Samuel), Recorte territorial
    (Vinícius), Capital escolar familiar e Rede de ensino de origem (Anselmo).
  - O Plano de Trabalho exige um módulo por integrante; o quarto módulo é
    escopo adicional. Se a Sprint 6 não comportar a versão v2 de Rede de
    ensino, o corte de escopo é registrado aqui até 07/11/2026, sem afetar o
    mínimo exigido.
- **Evidência:** `docs/apresentacao/AV2.md` (slide 11), `README.md` (integrantes).

## DL-03 — Regras do módulo Equidade socioeconômica

- **Data:** 02/11/2026
- **Responsável:** Samuel Silva de Rezende (autor do módulo)
- **Situação:** aceita
- **Contexto:** o Plano de Trabalho (Diretrizes, "Exemplo Prático de Cruzamento")
  descreve o módulo de equidade com dois cenários: (1) a posição real do
  usuário entre candidatos da mesma renda familiar; (2) a posição simulada da
  mesma nota entre alunos de escolas privadas de alta renda.
- **Decisão:**
  1. **Variável de renda:** `Q006` (renda mensal da família), mantida na TRUSTED
     como `renda_familiar`. O usuário escolhe a resposta com o texto exato do
     questionário da edição (valores em reais daquele ano, lidos de
     `docs/dicionario/dicionario_<ano>.json`).
  2. **Agrupamento em seis faixas**, em múltiplos do salário mínimo da edição,
     iguais em todas as edições porque as alternativas da Q006 já são múltiplos
     do salário mínimo:

     | Faixa | Alternativas Q006 | Renda familiar |
     | --- | --- | --- |
     | R1 | A, B | Até 1 salário mínimo (inclui "nenhuma renda") |
     | R2 | C, D | Mais de 1 até 2 SM |
     | R3 | E, F | Mais de 2 até 3 SM |
     | R4 | G, H | Mais de 3 até 5 SM |
     | R5 | I, J, K, L, M | Mais de 5 até 10 SM |
     | R6 | N, O, P, Q | Mais de 10 SM |

     As 17 alternativas não são usadas soltas porque as faixas altas (J a Q)
     têm entre 0,6% e 1,7% dos inscritos cada e, cruzadas com área e edição,
     ficariam instáveis para leitura. Seis faixas mantêm o gradiente de renda e
     deixam todo grupo muito acima do piso. Participação de cada faixa entre os
     inscritos (`docs/profiling/profiling_<ano>.json`, em %):

     | Edição | R1 | R2 | R3 | R4 | R5 | R6 |
     | --- | --- | --- | --- | --- | --- | --- |
     | 2019 | 29,5 | 35,5 | 13,8 | 9,7 | 7,3 | 4,2 |
     | 2020 | 40,5 | 30,5 | 12,0 | 7,3 | 4,9 | 3,1 |
     | 2021 | 33,5 | 29,8 | 13,1 | 10,2 | 8,7 | 4,8 |
     | 2022 | 35,3 | 28,7 | 12,5 | 11,0 | 7,8 | 4,6 |

     Em 2020, 1,66% dos inscritos não responderam à Q006.
  3. **Grupo de contraste:** participantes de **escola privada**
     (`TP_ESCOLA = 3`) com **renda familiar acima de 10 SM** (faixa R6). É um
     único grupo fixo, calculado no ETL.
  4. **Exceção ao bloqueio de cruzamentos da v1:** o contraste cruza duas
     variáveis (escola × renda). A regra geral da v1 proíbe cruzamentos porque
     geram grupos pequenos e permitem inferência por diferença. A exceção vale
     só para este grupo porque: ele é fixo (o usuário não escolhe o
     cruzamento); é grande (escola privada soma de 3,5% a 6,1% dos inscritos
     por edição); e passa pelo mesmo piso de 100 participantes por edição e área.
     Nenhum outro cruzamento é aberto por esta decisão.
  5. **Ausências e valores inválidos:**
     - `Q006` vazia (1,66% dos inscritos em 2020; residual, abaixo do piso, em 2021; nenhuma em 2019 e 2022): o participante fica
       fora das faixas de renda e do contraste, mas continua na comparação
       nacional.
     - `Q006` fora de A–Q: tratado como inválido, excluído das faixas e contado
       no manifesto local do ETL.
     - `TP_ESCOLA = 1` ("Não respondeu", de 62% a 76% dos inscritos, porque só
       concluintes do ensino médio no ano informam a escola) e `TP_ESCOLA = 4`
       ("Exterior", prevista no dicionário de 2019 e sem ocorrência nos dados):
       fora do contraste. O contraste, portanto,
       representa os **participantes que declararam escola privada**, e isso é
       informado na interface.
  6. **População:** a mesma do resto do produto: participantes elegíveis
     (presentes nos dois dias e não treineiros) com nota na área.
  7. **Piso:** grupo (edição × área × faixa ou contraste) com menos de 100
     participantes não é gerado. A interface informa "grupo insuficiente" e
     não mostra o cenário.
  8. **Medidas de cada cenário:** percentil exato (posto médio), mediana, média,
     desvio-padrão, Z-Score e tamanho do grupo. Entre os dois grupos: diferença
     de posição em pontos percentuais e probabilidade de superioridade
     P(faixa > contraste) + 0,5 · P(empate).
  9. **Artefato:** `data/analytics/dist_equidade.parquet` com as colunas
     `ano, area, recorte, grupo, nota, n, abaixo, total`, o mesmo esquema
     planejado para `dist_exata.parquet` por grupo (plano da Sprint 6). Quando
     o ETL por grupo do motor estiver pronto, o módulo passa a ler de lá sem
     mudar as regras. Uso restrito ao backend, como o `dist_exata.parquet`
     (ADR-001).
- **Fora do escopo:** renda per capita (Q006 ÷ Q005), cruzamento de renda com UF
  ou cor/raça, e qualquer leitura causal ("a renda causa a nota").
- **Evidência:** `scripts/equidade.py`, `app/pages/1_Equidade_socioeconomica.py`,
  `tests/test_equidade.py`.
