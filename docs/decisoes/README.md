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
| [DL-04](#dl-04--regras-do-módulo-recorte-territorial) | 02/11/2026 | Regras do módulo Recorte territorial | Vinícius (autor do módulo); aceite de Samuel (PO) em 03/11/2026 | Aceita |
| [DL-05](#dl-05--regras-do-módulo-capital-escolar-familiar) | 03/11/2026 | Regras do módulo Capital escolar familiar | Guilherme Anselmo (autor do módulo); aceite de Samuel (PO) em 08/11/2026 | Aceita |
| [DL-06](#dl-06--hospedagem-em-teste-no-replit) | 03/11/2026 | Hospedagem em teste no Replit | Samuel (PO) | Substituída em parte pela DL-08 |
| [DL-07](#dl-07--corte-do-módulo-rede-de-ensino-e-prazo-do-relatório-final-em-1911) | 08/11/2026 | Corte do módulo Rede de ensino e prazo do relatório final em 19/11 | Samuel (PO) | Aceita |
| [DL-08](#dl-08--replit-como-hospedagem-definitiva-e-publicação-beta) | 16/11/2026 | Replit como hospedagem definitiva e publicação beta | Samuel (PO) | Aceita |
| [DL-09](#dl-09--servidor-de-arquivos-estáticos-só-para-as-fontes) | 16/11/2026 | Servidor de arquivos estáticos só para as fontes | Guilherme Anselmo (front); registro do PO | Aceita |

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
  - *Atualização (08/11/2026):* o corte do Rede de ensino de origem foi decidido e
    está registrado na DL-07.
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
  10. **Limites de exibição do percentil** (acrescentado em 03/11/2026). A
      Equidade aplica a mesma regra da DL-04, item 8, com a mesma função
      (`exibir_percentil`, hoje em `scripts/estatistica.py`, movida de
      `scripts/territorial.py` em 08/11/2026): se a posição passar de
      100 × (N − 100) / N, a interface mostra "acima de X%"; se ficar abaixo de
      100 × 100 / N, "abaixo de X%"; nos demais casos, a posição exata. O
      percentil exato continua no backend. Quando um dos dois cenários está em
      limite, a diferença de posição entre eles não é exibida, porque somada à
      posição exata do outro cenário devolveria o valor escondido. A
      probabilidade de superioridade continua exibida: ela compara os dois
      grupos inteiros e não depende da nota digitada. Com os grupos reais (o
      menor tem 36.443 participantes), o limite cobre no máximo cerca de 0,3%
      de cada ponta. Motivo: coerência entre os módulos; a DL-04, item 8.10,
      registra que a diferença de tamanho dos grupos não elimina o risco.
- **Fora do escopo:** renda per capita (Q006 ÷ Q005), cruzamento de renda com UF
  ou cor/raça, e qualquer leitura causal ("a renda causa a nota").
- **Evidência:** `scripts/equidade.py`, `app/pages/1_Equidade_socioeconomica.py`,
  `tests/test_equidade.py`.

## DL-04 — Regras do módulo Recorte territorial

- **Data:** 02/11/2026
- **Responsável:** Vinícius Joacir dos Anjos (autor do módulo); aceite do PO: Samuel Silva de Rezende, em 03/11/2026
- **Situação:** aceita
- **Contexto:** o Plano de Trabalho (item 6, "Recorte territorial") pede comparar o
  desempenho com a UF, a região e a referência nacional da edição, com análise das
  diferenças de distribuição e do tamanho dos grupos. A privacidade (R5) trata o
  município como o campo de maior risco do contrato.
- **Decisão:**
  1. **Variável territorial:** `SG_UF_PROVA`, mantida na TRUSTED como `uf_prova`.
     É a UF do local de prova, preenchida para todos os inscritos nas quatro
     edições. `SG_UF_ESC` (UF da escola) fica de fora: falta para 64% a 76%
     dos elegíveis (64,1% em 2022, 76,0% em 2020), porque só quem conclui o
     ensino médio no ano informa a escola, e usá-la deixaria o módulo restrito
     a concluintes. A interface pergunta "Em qual UF você fez a prova?", não
     "onde você mora".
  2. **Três níveis**, sem cruzamento com outra variável:
     - **UF:** as 27 unidades federativas.
     - **Região:** as cinco regiões do IBGE (Norte, Nordeste, Sudeste, Sul,
       Centro-Oeste), derivadas da UF por tabela fixa em `scripts/territorial.py`.
     - **Brasil:** todos os elegíveis com UF válida.
  3. **Sem recorte municipal.** `CO_MUNICIPIO_PROVA` não é usado. Municípios
     pequenos ficariam abaixo do piso ou perto dele, e a diferença entre a UF e a
     soma dos municípios publicados permitiria deduzir os suprimidos (R3, "limite
     conhecido"). Fica para uma versão futura, se houver supressão complementar.
  4. **Códigos de grupo com prefixo** (`BR`, `RG-<região>`, `UF-<sigla>`): "SE" é
     a sigla de Sergipe e também a abreviação do Sudeste; sigla solta seria ambígua
     no artefato.
  5. **Ausências e valores inválidos:** `uf_prova` vazia ou fora das 27 siglas tira
     o participante de **todos** os grupos, inclusive do Brasil, para que UFs somem
     a região e regiões somem o Brasil sem resto. A contagem fica no manifesto
     local. Nas quatro edições reais não há nenhum caso.
  6. **População:** a mesma do resto do produto: participantes elegíveis (presentes
     nos dois dias e não treineiros) com nota na área. Por isso o "Brasil" do módulo
     é igual à CDF de `dist_exata.parquet`.
  7. **Piso:** grupo (edição × área × nível) com menos de 100 participantes não é
     gerado; a interface informa "grupo insuficiente". A menor UF (Roraima) tem
     cerca de 4 mil elegíveis em 2022, então nenhum grupo é suprimido hoje; a regra
     existe para edições futuras e para os testes.
  8. **Limites de exibição do percentil (UF e região).** Cumpre a pendência do R3
     de `docs/privacidade.md`: "o risco residual de inferência por consultas
     repetidas precisa ser reavaliado antes do deploy".
     1. **Problema.** Média, mediana, desvio e Z-Score são fixos por grupo; o
        percentil muda com a nota digitada. Quem testa notas seguidas mapeia as
        caudas de uma UF pequena: em Roraima, Matemática 2022 (3.984 elegíveis),
        nos extremos a mudança de posição entre duas notas vizinhas revela a nota
        de uma única pessoa (por exemplo, 885,4).
     2. **Limites por grupo**, com uma casa decimal:
        - superior: 100 × (N − `PISO_GRUPO`) / N, arredondado para baixo;
        - inferior: 100 × `PISO_GRUPO` / N, arredondado para cima.
     3. **Exibição.** Se o percentil p passar do limite superior, a interface
        mostra "acima de X%"; se ficar abaixo do inferior, "abaixo de X%"; nos
        demais casos, o percentil normal. Em Roraima, Matemática 2022, os limites
        são 97,4% e 2,6%. **Custo para o usuário:** o limite cobre no mínimo as
        cerca de 100 pessoas mais extremas, mas, como é arredondado para uma
        casa, nos grupos grandes cobre o 0,1% mais extremo: até cerca de 1,1 mil
        pessoas (Nordeste, 2019) perdem a posição exata. Em Matemática 2019, o
        ponto mais distante do topo ainda em limite fica a 106 pessoas em Roraima
        (7.654 participantes), 500 em São Paulo (501.136) e 1.116 na região
        Nordeste (1.116.723). Em 196 dos 640 grupos o limite alcança mais de 150
        pessoas.
     4. **Por que testar o percentil e não contar pessoas.** Com empates, contar
        pessoas gera rótulo falso. Exemplo: Minas Gerais, Redação 2020, N = 221.954,
        1.820 pessoas empatadas em 980 e 1 acima. A posição real é 99,59%, abaixo
        do limite superior de 99,9%, e a interface mostra 99,6%. A regra por
        contagem, com só 1 pessoa acima, diria "acima de 99,9%": um rótulo falso.
     5. **Por que comparar com o limite já arredondado.** Assim a ordem das
        posições exibidas nunca se inverte. Comparar com o limite sem arredondar
        não gera rótulo falso, mas em 281 dos 640 grupos uma nota maior aparece
        com posição menor que uma nota mais baixa (por exemplo, "100,0%" seguido
        de "acima de 99,9%"). Com o limite arredondado, os 640 grupos deram 0
        rótulos falsos e 0 inversões.
     6. **Alcance.** Vale para UF e região. O Brasil segue com percentil exato,
        conforme o ADR-001.
     7. **Dependência.** Quando a posição na UF estiver em limite, a diferença
        UF − Brasil não é exibida: somada ao percentil exato do Brasil, ela
        devolveria o valor escondido.
     8. **Grupo com menos de 200 participantes.** Os limites se cruzam e nunca há
        posição exata. Hoje não ocorre: o menor grupo real tem 3.984 participantes.
     9. **Risco residual.** Toda posição exata exibida tem pelo menos 100 pessoas
        de cada lado **contando os empatados pela metade** (abaixo + metade dos
        empatados ≥ 100, e o simétrico acima). Não vale contando só quem está
        estritamente abaixo: em Redação 2019, região Centro-Oeste, a nota 0
        aparece como 1,3% exato (1,25%) com zero pessoas abaixo, porque 6.241
        pessoas estão empatadas nela. Quando há menos de 100 pessoas estritamente
        de um lado, a nota é compartilhada por empatados, e são eles que
        completam a metade que falta. A auditoria registra 198 posições exatas
        com menos de 100 pessoas estritamente de um lado, todas por causa de
        empates. O menor empate tem só 3 pessoas: Sergipe, Linguagens 2019, nota
        331,7, com 99 pessoas abaixo, 3 empatadas e posição exibida de 0,2%.

        O meio da distribuição continua revelando notas: a posição exibida muda
        exatamente na nota de alguém, e quando essa nota é de uma só pessoa a
        mudança a revela. Isso é frequente em grupos pequenos, onde cada 0,1
        ponto percentual corresponde a poucas pessoas (cerca de 4 em Roraima):
        das 2.812 ocorrências com o limite, 2.714 estão em grupos com menos de
        100 mil participantes.

        Mudanças da posição exibida em nota de uma só pessoa. Varredura: grupos
        de UF e região, edição 2022, as quatro áreas objetivas (32 grupos × 4
        áreas = 128 combinações), notas de 0 a 1000 de 0,1 em 0,1:

        | Situação | Ocorrências | Combinações com ocorrência (de 128) |
        | --- | --- | --- |
        | Sem limite | 3.116 | 117 |
        | Com o limite | 2.812 | 116 |

        O limite elimina cerca de 10% das ocorrências. Aceitar esse risco é
        decisão do PO; aceito por Samuel em 03/11/2026 (ver "Aceite do PO", no
        fim desta entrada).
     10. **Por que a Equidade (DL-03) não tem esse limite.** O menor grupo da
         Equidade, o de contraste, tem cerca de 36 mil participantes, contra 3.984
         em Roraima: pela regra do item 8.2, o limite lá cobriria 0,3% do grupo,
         contra 2,6% aqui. É uma diferença de tamanho, não ausência de risco.
         *Atualização (03/11/2026):* por coerência entre os módulos, a Equidade
         passou a aplicar a mesma regra (DL-03, item 10).
     11. **Origem dos números.** Os itens 8.3, 8.4, 8.5 e 8.9 são reproduzidos por
         `scripts/auditoria_limites.py` sobre `dist_territorial.parquet` (saída em
         `data/analytics/_auditoria_limites.json`, fora do git; execução de
         03/11/2026, 40 s). A regra é testada em `tests/test_territorial.py`
         (`TestLimitesExibicao`, `TestAuditoria`).
  9. **Medidas:** em cada nível, percentil exato (posto médio), média, mediana,
     desvio-padrão, Z-Score e tamanho do grupo. Entre níveis:
     - diferença de posição UF − Brasil, em pontos percentuais, só quando a posição
       na UF não estiver em limite (item 8.7);
     - probabilidade de superioridade **UF contra o restante do Brasil** (Brasil
       sem a própria UF), P(UF > resto) + 0,5 · P(empate). Comparar com o Brasil
       inteiro incluiria a UF dos dois lados e puxaria o valor para 50%,
       principalmente em SP (cerca de 16% dos inscritos);
     - probabilidade de superioridade **região contra o restante do Brasil**
       (Brasil sem a própria região), mesma fórmula;
     - posição da mediana da UF entre as 27 (1 = maior). UFs com a mesma mediana
       dividem a posição (1 + número de UFs com mediana estritamente maior) e a
       interface diz com quantas está empatada. A sigla não desempata. Há
       empates em 9 das 20 combinações de edição e área, entre elas as 4 da
       Redação, onde a mediana é múltipla de 20.
  10. **Conferências antes de publicar:** (a) CDF em SQL igual à montada em Python;
      (b) UFs somam a região e regiões somam o Brasil, nota a nota, antes do piso;
      (c) percentil da CDF igual à contagem direta na TRUSTED. Qualquer falha aborta
      e não deixa artefato parcial.
  11. **Artefato:** `data/analytics/dist_territorial.parquet` com as colunas
      `ano, area, recorte, grupo, nota, n, abaixo, total`, mesmo esquema do
      `dist_equidade.parquet`. Uso restrito ao backend (ADR-001).
- **Fora do escopo:** município, UF da escola, cruzamento de território com renda,
  cor/raça ou rede de ensino, e leitura causal ("o estado causa a nota"). As UFs
  diferem em renda, rede e perfil de quem faz a prova; a interface diz isso.
- **Evidência:** `scripts/territorial.py`, `scripts/auditoria_limites.py`,
  `app/pages/2_Recorte_territorial.py`, `tests/test_territorial.py`.
- **Aceite do PO (Samuel Silva de Rezende, 03/11/2026):** aceita integralmente,
  inclusive o risco residual do item 8.9, revisado no PR #12. Motivos:
  1. **A fonte já é pública.** O INEP publica os microdados com a nota de cada
     participante e a UF de prova; a nota de um participante anônimo pode ser
     obtida no próprio arquivo oficial. O app não revela informação que não
     esteja na fonte e não carrega identificador (`NU_INSCRICAO` é descartado na
     TRUSTED).
  2. **Os limites acrescentam proteção sem distorcer o resultado:** 0 rótulos
     falsos e 0 inversões nos 640 grupos auditados, e o item 8.7 impede recuperar
     a posição escondida pela diferença UF − Brasil.
  3. **O custo para o usuário é pequeno:** nos grupos grandes, só o 0,1% mais
     extremo perde a posição exata.

  Consequência: a mesma regra passa a valer na Equidade (DL-03, item 10).

## DL-05 — Regras do módulo Capital escolar familiar

- **Data:** 03/11/2026
- **Responsável:** Guilherme da Silva Anselmo (autor do módulo)
- **Situação:** aceita pelo PO (Samuel Silva de Rezende) em 08/11/2026, na revisão do PR #15
- **Contexto:** o Plano de Trabalho (módulos autorais) pede que o módulo compare
  o usuário por escolaridade dos responsáveis, com forte controle de categorias,
  ausências, integridade e tamanho de grupo. As variáveis são `Q001` (pai) e
  `Q002` (mãe), com as mesmas alternativas A a H nas quatro edições
  (conferido em `docs/dicionario/`). H significa "Não sei" e é uma resposta
  válida, diferente de campo vazio.
- **Decisão:**
  1. **Variáveis:** o usuário informa `Q001` e `Q002` (A a H).
  2. **Grupo do participante:** o maior nível de escolaridade informado entre
     pai e mãe (A a G). Se um deles for H ou vazio, vale o outro.
     **Limitação conhecida:** com pai = H e mãe = A, o participante entra no
     nível A, embora o pai possa ter escolaridade maior. Isso é dito na
     interface. O caso é mais comum do lado do pai: H aparece em 8,7% a 9,6%
     das respostas da `Q001` e em 2,7% a 3,2% das da `Q002`, conforme a edição
     (`docs/profiling/profiling_<ano>.json`). Grupos por par (pai × mãe) geram 64 combinações por edição e
     área, com risco de células pequenas (R3), e por isso não são usados.
  3. **Sem informação nos dois:** pai e mãe H ou vazios deixam o participante
     fora dos grupos de escolaridade, mas ele continua na comparação nacional.
     Não existe nível a atribuir, e um grupo "Não sei" misturaria todos os
     níveis, sem significado para o módulo. O mesmo vale para a entrada do
     usuário: se ele responder H nos dois campos, o módulo informa que não há
     nível para comparar e mostra só a posição nacional.
  4. **Seis níveis:** A; B e C (Fundamental incompleto); D; E; F; G. B e C são
     juntados porque ambos significam "não terminou o Fundamental". Os demais
     ficam separados porque cada um marca uma etapa concluída diferente. Não há
     junção por tamanho do grupo: a menor alternativa (A) tem pelo menos 2,6%
     dos inscritos em cada campo, cerca de 89 mil pessoas (`Q002`, 2022).
     Participação de cada nível entre os inscritos, por campo
     (`docs/profiling/profiling_<ano>.json`, em %):

     | Edição | Campo | A | B e C | D | E | F | G | H |
     | --- | --- | --- | --- | --- | --- | --- | --- | --- |
     | 2019 | `Q001` (pai) | 5,7 | 36,5 | 11,5 | 25,7 | 7,4 | 4,5 | 8,7 |
     | 2019 | `Q002` (mãe) | 3,8 | 30,2 | 13,1 | 32,1 | 10,1 | 7,8 | 2,9 |
     | 2020 | `Q001` (pai) | 5,8 | 37,4 | 10,6 | 25,0 | 6,6 | 4,1 | 8,7 |
     | 2020 | `Q002` (mãe) | 4,1 | 31,7 | 12,1 | 31,1 | 9,2 | 7,5 | 2,7 |
     | 2021 | `Q001` (pai) | 4,4 | 32,2 | 11,0 | 28,2 | 9,1 | 6,5 | 8,7 |
     | 2021 | `Q002` (mãe) | 2,9 | 25,4 | 11,8 | 33,9 | 12,1 | 11,2 | 2,7 |
     | 2022 | `Q001` (pai) | 4,0 | 30,4 | 11,2 | 28,8 | 9,1 | 6,8 | 9,6 |
     | 2022 | `Q002` (mãe) | 2,6 | 23,5 | 11,9 | 35,0 | 12,2 | 11,6 | 3,2 |

     Em 2020, 1,66% dos inscritos não responderam aos dois campos; em 2021 o
     vazio é residual, abaixo do piso; em 2019 e 2022 não há. O profiling
     conta cada campo separado, entre todos os inscritos; o nível do
     participante (o maior dos dois) não aparece nele. O nível A real é menor
     que as duas colunas A, porque exige que nenhum dos dois tenha nível
     maior. O ETL confere os tamanhos reais por edição, área e nível e
     registra no manifesto.
  5. **Cenários:** por padrão a interface mostra um cenário, a posição entre
     participantes do mesmo nível. A comparação com outro nível é **opcional**
     (caixa de seleção). Motivo: a comparação pode causar desconforto em quem a
     lê como ranking de pessoas. A linguagem é neutra e descritiva ("a mesma
     nota fica em posições diferentes conforme o grupo"), sem juízo sobre
     capacidade.
  6. **Nível de comparação:** o nível imediatamente acima do usuário. A
     comparação com o vizinho é mais informativa do que com o extremo. Se o
     nível vizinho estiver abaixo do piso naquela edição e área, a comparação
     não é exibida e a interface informa "grupo insuficiente". O módulo não
     pula para o nível seguinte: isso mudaria a comparação sem o usuário
     escolher. Não é esperado, mas ainda não foi medido: o menor campo
     isolado tem cerca de 89 mil inscritos (`Q002` = A, 2022), e o tamanho
     real de cada nível entre os elegíveis, por edição e área, sai do ETL, que
     confere e registra no manifesto. A regra existe para edições futuras e
     para os testes.
  7. **Nível mais alto (G):** compara com o nível imediatamente abaixo (F). O
     texto da interface diz "abaixo" nesse caso.
  8. **Valores inválidos:** `Q001` ou `Q002` fora de A a H tira o participante
     dos grupos de escolaridade, mantém na comparação nacional e é contado no
     manifesto local do ETL. Não vira "H": um código inexistente é erro de dado,
     não resposta "Não sei".
  9. **Um campo inválido contamina o registro:** com um dos dois campos
     inválido, o registro inteiro fica fora dos grupos, mesmo que o outro seja
     válido. Um campo corrompido reduz a confiança no registro todo.
  10. **População:** a mesma do resto do produto: participantes elegíveis
      (presentes nos dois dias e não treineiros) com nota na área.
  11. **Piso:** grupo (edição × área × nível) com menos de 100 participantes não
      é gerado. A interface informa "grupo insuficiente".
  12. **Medidas:** percentil exato (posto médio), mediana, média, desvio-padrão,
      Z-Score e tamanho do grupo. Na comparação: diferença de posição entre os
      dois níveis, em pontos percentuais, e probabilidade de superioridade
      P(nível do usuário > nível de comparação) + 0,5 · P(empate), a mesma
      fórmula da DL-03 e da DL-04.
  13. **Limites de exibição do percentil:** aplica a regra da DL-04, item 8,
      **importando** `exibir_percentil` de `scripts/estatistica.py` (função
      compartilhada), sem copiar.
      Se um dos cenários estiver em limite, a diferença de posição entre eles
      não é exibida. A probabilidade de superioridade continua exibida, como
      na DL-03, item 10: ela compara os dois níveis inteiros e não depende da
      nota digitada. Motivo: coerência entre os módulos e fonte única da regra.
  14. **Artefato:** `data/analytics/dist_capital.parquet` com as colunas
      `ano, area, recorte, grupo, nota, n, abaixo, total`, mesmo esquema dos
      demais módulos. Uso restrito ao backend (ADR-001).
- **Fora do escopo:** cruzamento da escolaridade com renda, UF ou município,
  cor/raça e rede de escola (os três primeiros por risco de células pequenas e
  dado sensível, R3 a R5; o último por ser o módulo Rede de ensino); ocupação
  dos pais (outro tema, sem ganho para a pergunta do módulo); e leitura causal
  ("a escolaridade dos pais causa a nota").
- **Evidência:** `scripts/capital_escolar.py` (regras, agregação offline e
  comparação), `app/pages/3_Capital_escolar_familiar.py` (página) e
  `tests/test_capital_escolar.py` (testes com microdados sintéticos). O
  artefato `data/analytics/dist_capital.parquet` é gerado por
  `scripts/capital_escolar.py` e fica fora do git (ADR-001). O módulo importa
  `exibir_percentil` de `scripts/estatistica.py`, sem copiar (item 13), e não
  importa os outros módulos autorais (`tests/test_modulos_independentes.py`). A execução com os microdados
  reais de 2019 a 2022 (10/11/2026) está em `docs/modulos/capital-escolar-resultados.md`.

## DL-06 — Hospedagem em teste no Replit

- **Data:** decisão em 03/11/2026; registro em 08/11/2026
- **Responsável:** Samuel Silva de Rezende (Product Owner). A hospedagem estava com
  Vinícius no plano da Sprint 6; o PO assume a tentativa no Replit para cumprir o
  prazo do relatório final, que exige o link público. O prazo passou a ser
  19/11/2026 (DL-07).
- **Situação:** decidida, primeira publicação ainda não feita (prevista até 13/11/2026, DL-07). Pode ser revista antes ou depois dessa publicação.
  *Atualização (16/11/2026):* a publicação de 13/11/2026 não foi feita. Ela depende do aplicativo
  completo, com os três módulos e a interface revisada; o código do Capital escolar entrou em
  10/11/2026 à noite, o capítulo 3 só foi entregue em 15/11/2026 e a nova interface (PR #30),
  aprovada em 15/11, só foi mesclada em 16/11/2026 à 01h15. O PO remarcou a primeira publicação para a etapa final, antes da entrega de
  19/11/2026, como registrado no README (PR #18) e no relatório consolidado da AV4.
  *Atualização (17/11/2026):* o caráter de "teste" e a troca de provedor como saída
  foram substituídos pela DL-08: o Replit passa a ser a hospedagem definitiva, com
  publicação beta depois do merge das atualizações da AV6. Os critérios desta entrada continuam como
  critérios de operação.
  *Atualização (19/11/2026):* a primeira publicação foi feita em 19/11/2026, às 00:10, em
  <https://radarenem-projetoaplicado3-kirasapiens.replit.app> (DL-08). Resultado dos quatro
  pontos testados: (1) o `.replit` do repositório funcionou na importação, com
  `deploymentTarget = "vm"` acrescentado para a Reserved VM; (2) o projeto ficou privado, os
  artefatos ficaram fora do git e o `checar_saude.py` não conseguiu baixar nenhum deles;
  (3) consulta p95 entre 70 e 416 ms, primeira abertura do territorial em 4,1 s e pico de
  cerca de 838 MiB na publicação, dentro dos 2 GB; (4) créditos: a Reserved VM custa cerca de
  US$ 15 por mês, a conferir no painel até a banca. Nenhum critério de revisão foi atingido.
  Medições em `docs/deploy/replit.md` e `docs/deploy/medicoes/`.
- **Contexto:** `docs/av3/EVOLUCAO-FUTURA-NUVEM.md` deixou a hospedagem em aberto, com
  o Azure apenas como exemplo. O app precisa de quatro artefatos agregados que não
  vão para o GitHub (`docs/privacidade.md`, R1) e não podem ser baixados pelo público
  (ADR-001).
- **Decisão:** primeira tentativa no Replit, na conta do PO (plano Core), com o código
  importado do GitHub e os artefatos enviados direto ao projeto privado. Configuração
  em `.replit`; procedimento em `docs/deploy/replit.md`.
- **Critérios:**
  1. **Privacidade dos artefatos.** O Replit aceita arquivos fora do git no projeto;
     com o projeto privado, eles ficam só no backend. Em plataformas que publicam a
     partir do repositório, os artefatos teriam de ir para o git ou ser buscados de
     outro armazenamento, o que o R1 não permite sem trabalho adicional.
  2. **Custo.** Os créditos mensais do plano Core cobrem a máquina compartilhada sempre
     ligada (0,5 vCPU, 2 GB). Os créditos também pagam o agente de IA do Replit; o uso
     do agente fica fora deste projeto para não consumir a hospedagem.
  3. **Memória e tempo de resposta.** Teste local com os artefatos reais (03/11/2026,
     2 vCPU): cerca de 600 MB com as três páginas abertas e respostas entre 0,4 e 1,4 s,
     dentro do limite de 3 s. A primeira abertura do Recorte territorial levou 10,4 s
     (2,2 milhões de linhas em memória); as seguintes, 2,2 s.
- **Alternativas consideradas:** Streamlit Community Cloud e Hugging Face Spaces,
  citados na AV2 (gratuitos, mas publicam a partir de um repositório, o que expõe os
  artefatos ou exige armazenamento à parte), e Azure, citado na AV3 como exemplo
  (mais configuração e custo fora do plano já pago).
- **Riscos:** dependência de uma conta pessoal; primeiro acesso lento depois de
  reiniciar (mitigado com a máquina sempre ligada e abertura das páginas após cada
  publicação); a máquina compartilhada pode ser mais lenta que o teste local, então as
  medições no Replit precisam ser registradas em `docs/deploy/replit.md`.
- **O que está sendo testado:**
  1. se o `.replit` do repositório funciona na importação (o formato foi montado a
     partir de exemplos, não da documentação oficial, e só se confirma no Replit);
  2. se o projeto fica privado com os artefatos fora do git, sem nenhum caminho de
     download para o público;
  3. memória e tempo de resposta na máquina compartilhada do Replit, mais lenta que o
     teste local, sobretudo a primeira abertura do Recorte territorial;
  4. se os créditos mensais do plano Core bastam para manter a máquina sempre ligada
     até a banca (01/12/2026).
- **O que o PO está aguardando:**
  - o módulo Capital escolar completo do Anselmo (código, documentação e capítulo
    autoral) até 10/11/2026 (DL-07), antes de publicar a versão com os três módulos;
  - a definição do front, que pode ser construído no próprio Replit, mantendo o GitHub
    como fonte oficial e cada integrante commitando com a própria conta (rastreabilidade
    da AV4). Os papéis de front, QA e otimização são fechados depois de 10/11, conforme o
    que estiver pronto; se preciso, o PO assume o que faltar.
- **Quando a decisão é revista:** se alguma consulta passar de 3 s com a máquina
  sempre ligada, se não for possível garantir o projeto privado, ou se os créditos não
  cobrirem a hospedagem até a banca. Nesses casos, a equipe volta às alternativas acima,
  e a escolha nova entra como DL substituta desta.
- **Prioridade que orienta a decisão:** entregar o projeto nas datas dos professores
  (relatório final com link público em 19/11/2026, DL-07; banca em 01/12/2026), mesmo que
  o PO assuma responsabilidades originalmente de outro integrante.
- **Evidência:** `.replit`, `docs/deploy/replit.md`.

## DL-07 — Corte do módulo Rede de ensino e prazo do relatório final em 19/11

- **Data:** 08/11/2026
- **Responsável:** Samuel Silva de Rezende (Product Owner)
- **Situação:** aceita
- **Contexto:**
  - O professor Hugo, de Engenharia de Dados, que tem entrega compartilhada com o
    Projeto Aplicado, exigiu o relatório final de tudo até **19/11/2026**. A data do AVA
    (24/11/2026) deixa de ser a referência da equipe.
  - A DL-02 previa decidir até 07/11/2026 o corte do quarto módulo (Rede de ensino de
    origem) se a Sprint 6 não o comportasse. Em 08/11/2026 o módulo não tem regra,
    branch nem código; o Capital escolar familiar, do mesmo integrante, tem as regras
    aceitas (DL-05, PR #15) e o código ainda por fazer.
- **Decisão:**
  1. **Novo prazo final:** relatório final consolidado e app publicado na nuvem até
     19/11/2026.
  2. **Corte de escopo:** o módulo Rede de ensino de origem sai do escopo. O Plano de
     Trabalho exige um módulo por integrante; os três módulos (Equidade, Recorte
     territorial e Capital escolar familiar) atendem ao mínimo. O tema fica registrado
     como evolução futura, sem regra aprovada.
  3. **Prazo do Capital escolar familiar:** 10/11/2026, incluindo código, página e
     testes em PR com CI verde, documentação atualizada e o capítulo autoral da AV4.
     Se algum item não couber, o PO redistribui o trabalho.
  4. **Cronograma até a entrega:**

     | Até | Marco |
     | --- | --- |
     | 10/11/2026 | Módulos e capítulos autorais da AV4 fechados |
     | 13/11/2026 | App publicado no Replit (DL-06) e front ajustado |
     | 15/11/2026 | QA e otimização |
     | 17/11/2026 | Relatório final em rascunho, revisado pelos três |
     | 19/11/2026 | Entrega do relatório final |

  5. **Papéis de front, QA e otimização:** definidos pelo PO depois de 10/11/2026,
     conforme o que estiver pronto. Se necessário, o PO assume responsabilidades
     originalmente de outro integrante para cumprir as datas.
- **Atualização (16/11/2026), situação do cronograma:**
  - **10/11 – módulos e capítulos da AV4:** os três módulos estavam no `main` em 10/11 (PRs #10,
    #12 e #20). O capítulo 1 foi entregue em 02/11 e atualizado em 15/11; o capítulo 2, em 10/11
    (PR #19), com a versão em Word em 15/11 (PRs #28 e #31); o capítulo 3, em 15/11 (PR #29),
    cinco dias depois do prazo, após a cobrança nas issues #25 e #26.
  - **13/11 – publicação no Replit:** remarcada para a etapa final (ver DL-06).
  - **15/11 – QA e otimização:** parcial. Os papéis não foram formalizados, por dependência dos
    itens acima; houve a revisão de segurança do `.gitignore` (PR #27) e a nova interface
    (PR #30, mesclada em 16/11/2026, depois do envio da AV4). O QA da aplicação completa e a otimização passam
    para a AV6.
  - **AV4:** relatório consolidado em `docs/av4/`, entregue no AVA.
  - **17/11 e 19/11:** mantidos para o relatório final (AV6).
- **Substitui:** o prazo de 24/11/2026 usado como referência nas DL-05 e DL-06 e no
  plano da Sprint 6; completa a DL-02 (corte do quarto módulo).
- **Evidência:** revisão do PO no PR #15 (08/11/2026) e mensagem ao grupo da equipe
  na mesma data.

## DL-08 — Replit como hospedagem definitiva e publicação beta

- **Data:** 16/11/2026
- **Responsável:** Samuel Silva de Rezende (Product Owner)
- **Situação:** aceita
- **Substitui em parte:** DL-06 (o caráter de teste e a volta às alternativas como saída).
- **Contexto:** a DL-06 colocou o Replit em teste, com a troca de provedor como saída se
  algum critério falhasse. A publicação prevista para 13/11 (DL-07) não aconteceu, e o
  relatório final de 19/11 exige o link público com a aplicação validada (30% da AV6).
  Não há tempo para avaliar outro provedor, e o Plano de Trabalho (objetivo 8) pedia uma
  versão beta antes da final.
- **Decisão:**
  1. **Hospedagem definitiva no Replit**, na conta do PO, plano Core, tipo Reserved VM
     com máquina compartilhada (0,5 vCPU, 2 GB), sempre ligada. Justificativa do modelo
     de serviço, custos e comparação com a arquitetura de referência da disciplina de
     Computação em Nuvem em `docs/av6/nuvem.md`.
  2. **Publicação beta depois do merge deste PR na `main`** (prevista para 17/11/2026), com os cinco artefatos da
     execução de referência (hashes em `docs/deploy/artefatos.sha256`). A beta serve para
     medir no ambiente real e para o teste de usabilidade; as correções da AV6 entram por
     PR e são republicadas.
  3. **Barreira antes de cada publicação:** `scripts/auditar_artefatos.py` precisa terminar
     com OK (colunas, chave do grão, piso por grupo, coerência das CDFs, Brasil igual entre
     artefatos e hash). Depois de publicar, `scripts/checar_saude.py` confere a resposta e
     que nenhum artefato pode ser baixado.
  4. **Agente de IA do Replit:** a DL-06 deixava o agente fora do projeto, para não
     consumir os créditos da hospedagem. Ele passa a ser usado só para configurar a
     publicação (importação, dependências, auditoria e tipo de publicação), com um
     prompt fechado escrito pela equipe e versionado em `docs/deploy/`. O agente não
     altera código do produto; qualquer mudança de código continua entrando por PR no
     GitHub. O consumo de créditos é conferido no painel antes e depois.
  5. **Se um critério da DL-06 falhar** (consulta acima de 3 s, projeto não privado ou
     créditos insuficientes até a banca), a primeira resposta passa a ser dentro do
     próprio Replit: VM dedicada (1 vCPU, 4 GB) para desempenho ou memória; ajuste de
     créditos para custo. Trocar de provedor só com DL nova.
- **O que está sendo testado na beta:** memória com as quatro páginas abertas (no ambiente
  de desenvolvimento, em 16/11, o pico foi de cerca de 1,2 GB com as quatro páginas no
  mesmo processo, o dobro da estimativa de 03/11); tempo de consulta no ambiente real;
  tempo para recriar a publicação do zero (RTO).
- **Atualização (19/11/2026), beta publicada:**
  - **Quando e onde:** publicada em 19/11/2026, às 00:10 (horário de Brasília), em
    <https://radarenem-projetoaplicado3-kirasapiens.replit.app>, Reserved VM compartilhada
    (0,5 vCPU, 2 GB), região South America, monitoramento ligado, análises de visitantes e
    widget de feedback desligados (R6).
  - **Atraso em relação a 17/11:** o filtro de pacotes do Replit recusou o Pillow 12.x
    (CVE-2026-112900), o que levou ao Streamlit 1.66.1 e ao Pillow 13.0.0 (PR #35). Depois, a
    verificação de segurança da tela Publish bloqueou a publicação por versões supostas de
    dependências indiretas; a correção foi fixá-las no `requirements.txt` e o setuptools no
    `requirements-benchmark.txt` (PR `deps-fixar-transitivas`).
  - **Uso do agente (item 4):** o agente seguiu o prompt de `docs/deploy/prompt-agente-replit.md`
    e não alterou código do produto. A exceção foi a correção automática do Centro de
    segurança ("Corrigir tudo com Agent"), acionada pelo PO, que fixou as mesmas versões num
    commit local do Replit. Esse commit não foi enviado ao GitHub; a mesma mudança entrou pelo
    PR `deps-fixar-transitivas`, com revisão.
  - **Resultado:** as quatro páginas mostraram o resultado pelo link público; consulta p95
    entre 70 e 416 ms (meta de 3 s); pico de cerca de 838 MiB na publicação; nenhum artefato
    exposto. O item 5 (VM dedicada) não foi necessário. Ficam para a AV6 o tempo até o
    resultado no navegador (teste de usabilidade) e o RTO.
- **Evidência:** `docs/deploy/replit.md` (passo a passo e tabela de medições),
  `docs/av6/nuvem.md`, `docs/deploy/medicoes/`, `scripts/auditar_artefatos.py`,
  `scripts/checar_saude.py`, `scripts/medir_desempenho.py`.

## DL-09 — Servidor de arquivos estáticos só para as fontes

- **Data:** registro em 16/11/2026; a mudança entrou no PR #30 (commit `b888e0b`, 15/11/2026)
- **Responsável:** Guilherme da Silva Anselmo (autor do front); registro do PO
- **Situação:** aceita
- **Contexto:** `docs/av3/EVOLUCAO-FUTURA-NUVEM.md` (seção 7) recomendava não habilitar o
  serviço de arquivos estáticos do Streamlit, para não haver nenhum caminho de download
  perto dos artefatos. O front novo passou a servir as fontes IBM Plex de `app/static/`
  (`enableStaticServing = true`), para não pedir as fontes ao Google, o que enviaria o IP
  de cada visitante a um terceiro (R6).
- **Decisão:** manter o servidor de estáticos ligado, com estas condições:
  1. `app/static/` só contém as fontes e a licença OFL; nenhum dado vai para essa pasta;
  2. os artefatos ficam em `data/analytics/`, fora da pasta servida;
  3. caminho com `..`, inclusive codificado, é recusado pelo Streamlit com HTTP 400
     (conferido em 15/11/2026 e em 16/11/2026);
  4. a conferência é automática: `scripts/checar_saude.py` tenta baixar os cinco artefatos
     por caminhos diretos e pelo servidor de estáticos e falha se algum responder com um
     Parquet.
- **Alternativa descartada:** fontes do Google Fonts (terceiro recebe o IP do visitante) ou
  fontes do sistema (perde a identidade visual do front).
- **Evidência:** `.streamlit/config.toml`, `app/static/fonts/`, `scripts/checar_saude.py`.
