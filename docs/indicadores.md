# Dicionário de indicadores — Radar ENEM

Contrato de cada número exibido no app, no formato de contrato de KPI da disciplina de
Business Intelligence e Data Visualization (aula de KPIs e performance): identificador,
pergunta que responde, fórmula, universo, unidade, arredondamento, contexto, fonte,
qualidade e regra de exibição. As regras de origem estão nas decisões citadas; este
documento não cria regra nova, só reúne o que já foi decidido.

O Radar ENEM não tem metas nem semáforos: os números descrevem a posição de uma nota e
não pedem uma ação do usuário. Por isso os campos "meta", "limiar de alerta" e
"responsável pela ação" dos contratos de KPI não se aplicam. O "dono" de cada indicador é
o autor do módulo que o exibe.

## Campos comuns a todos os indicadores

| Campo | Valor |
| --- | --- |
| Fonte | Microdados do ENEM 2019 a 2022 (INEP), arquivos identificados por SHA-256 em `data/raw/hashes.sha256` |
| Universo | Participantes elegíveis da edição: presentes nos dois dias e não treineiros, com nota na área (relatório da AV3, seção 3.5) |
| Grão | Edição × área × grupo de comparação |
| Atualização | Estática. Uma execução do pipeline por edição publicada pelo INEP; data e commit no rodapé do app (`_manifesto_publicacao.json`) |
| Piso | Nenhum grupo com menos de 100 participantes é exibido (`PISO_GRUPO`, R3) |
| Dado do usuário | Notas e atributos digitados não são gravados (R6) |
| Leitura | Descritiva. Nenhum indicador é efeito causal nem previsão de aprovação |

## Indicadores

### IND-01 — Percentil (posição da nota)

| Campo | Valor |
| --- | --- |
| Pergunta | Em que posição a minha nota fica entre os participantes deste grupo? |
| Fórmula | (abaixo + iguais / 2) / N × 100, posto médio, sem interpolação |
| Unidade e direção | %, maior significa mais participantes com nota abaixo |
| Arredondamento | 1 casa decimal, só na exibição (DL-01) |
| Exibição protegida | Em UF, região, faixa de renda e nível de escolaridade: "acima de X%" ou "abaixo de X%" perto das pontas, com X = 100 · (N − 100) / N ou 100 · 100 / N (DL-04, item 8). Nacional: exato (ADR-001) |
| Gráfico | Anel com o valor e métrica em texto; histograma com faixas de pelo menos 100 pessoas |
| Código | `percentil_exato_acumulado`, `exibir_percentil` em `scripts/estatistica.py` |
| Dono | Motor estatístico (Samuel, ADR-001; Vinícius, motor v1) |

### IND-02 — Média, mediana e desvio-padrão do grupo

| Campo | Valor |
| --- | --- |
| Pergunta | Como é o grupo com que estou sendo comparado? |
| Fórmula | Média e variância populacionais (divisor N); mediana = menor nota com pelo menos 50% de N nela ou abaixo (mediana inferior) |
| Unidade | Pontos de nota, 1 casa decimal |
| Código | `resumo`, `quantil` |
| Dono | Motor estatístico (DL-01) |

### IND-03 — Quartis e caixa protegida

| Campo | Valor |
| --- | --- |
| Pergunta | Entre que notas está a metade central dos participantes? |
| Fórmula | Q1, mediana e Q3 pela regra de `quantil` com p = 0,25, 0,5 e 0,75; bigodes em P5 e P95 |
| Unidade | Pontos de nota, 1 casa decimal |
| Exibição protegida | Sem mínimo, máximo nem pontos discrepantes; caixa só com N ≥ 2.000 (5% de N ≥ piso) |
| Gráfico | Boxplot horizontal com a nota do usuário marcada (página inicial) |
| Código | `caixa_protegida` |
| Dono | Motor estatístico (AV6, `docs/av6/estatistica.md`) |

### IND-04 — Z-Score

| Campo | Valor |
| --- | --- |
| Pergunta | A quantos desvios-padrão da média do grupo está a minha nota? |
| Fórmula | (nota − média) / desvio |
| Unidade | Desvios-padrão, 2 casas |
| Cuidado | Não é convertido em percentil pela curva normal: nos dados reais, Φ(z) erra o percentil em até 8,6 pontos percentuais (`docs/av6/estatistica.md`, seção 5) |
| Código | `z_score` |

### IND-05 — Diferença de posição

| Campo | Valor |
| --- | --- |
| Pergunta | Quanto muda a minha posição de um grupo para o outro? |
| Fórmula | percentil no grupo A − percentil no grupo B, em pontos percentuais |
| Unidade e direção | pp; positivo significa posição melhor no grupo A |
| Exibição protegida | Não exibida quando um dos dois percentis está em limite: somada à posição exata do outro grupo, revelaria o valor escondido (DL-03, item 10; DL-04, item 8.7) |
| Onde | Equidade (faixa × contraste), Recorte territorial (UF × Brasil), Capital escolar (nível × vizinho) |

### IND-06 — Probabilidade de superioridade

| Campo | Valor |
| --- | --- |
| Pergunta | Sorteando uma pessoa de cada grupo, qual a chance de a do primeiro ter nota maior? |
| Fórmula | P(A > B) + 0,5 · P(A = B) = U de Mann-Whitney / (n_A · n_B) |
| Unidade e direção | %, 1 casa; 50% significa grupos equivalentes |
| Leitura | Tamanho de efeito (McGraw e Wong, 1992), sem p-valor (`docs/av6/estatistica.md`, seção 3) |
| Particularidade | No Recorte territorial, a UF e a região são comparadas com o restante do Brasil, sem elas mesmas (DL-04, item 9) |
| Código | `prob_superioridade` |

### IND-07 — Posição da mediana da UF

| Campo | Valor |
| --- | --- |
| Pergunta | Onde está a mediana da minha UF entre as 27? |
| Fórmula | 1 + número de UFs com mediana estritamente maior; empatadas dividem a posição |
| Gráfico | Pontos (dot plot), com o N de cada UF no rótulo do eixo |
| Código | `medianas_ufs`, `posicao_da_mediana` em `scripts/territorial.py` |
| Dono | Vinícius (DL-04) |

### IND-08 — Tamanho do grupo (N)

| Campo | Valor |
| --- | --- |
| Pergunta | Com quantas pessoas estou sendo comparado? |
| Fórmula | Total de elegíveis do grupo com nota na área |
| Exibição | Sempre ao lado do resultado; grupo abaixo de 100 vira "grupo insuficiente" |

## Checklist de BI aplicado (aula de dashboards e checklist de indicadores auditáveis)

| Item | Situação |
| --- | --- |
| Pergunta de negócio por visual | Atendido: cada página abre com a pergunta do módulo |
| Fórmula, universo, período e N por indicador | Atendido neste documento e na tela (N sempre visível) |
| Barras começam em zero | Atendido. O gráfico de medianas era de barras com eixo truncado e virou dot plot (AV6) |
| Fonte e data de atualização visíveis | Atendido: rodapé em todas as páginas (AV6) |
| Informação essencial fora do passar do mouse | Atendido: N das UFs passou para o rótulo do eixo (AV6) |
| Contraste e cor não como único código | Atendido: cores com 3:1 nos dois temas, conferidas em teste; a nota também é marcada por linha tracejada ou losango |
| SQL dinâmica parametrizada | Atendido: o app lê os artefatos com `read_parquet(?)` |
| Medição de p50/p95 | Em andamento: `scripts/medir_desempenho.py` e `docs/deploy/replit.md` |
| Teste com público-alvo | Em andamento: protocolo em `docs/qa/teste-usabilidade.md` |
