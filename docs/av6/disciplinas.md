# AV6 — Técnicas das disciplinas usadas e não usadas no Radar ENEM

Levantamento pedido para o relatório final: para cada disciplina do semestre (e duas do
semestre anterior que o projeto aplica), quais técnicas o projeto usou, onde está a
evidência, quais não usou e por quê, e o que mudou na AV6 a partir desse cruzamento.

**Base do cruzamento.** Material didático das disciplinas consolidado pelo PO em
16/11/2026 (planos de ensino, aulas e laboratórios disponíveis no AVA). O nível de
evidência é mantido no texto: quando a disciplina só tem ementa ou plano disponível
(Estatística I e Banco de Dados II), a técnica é citada como "prevista na ementa", e não
como conteúdo de aula.

| Disciplina | Semestre | Material disponível |
| --- | --- | --- |
| Big Data | 2026/2 | Plano de ensino e três aulas |
| Engenharia de Dados e MLOps | 2026/2 | Plano de ensino, aulas 1 a 8 e 10, laboratórios de manutenção preditiva e de data drift |
| Computação em Nuvem | 2026/2 | Plano de ensino, aulas 1 a 9, revisão e aula de redes virtuais |
| Estatística I | 2026/2 | Ementa (sem material de aula no AVA) |
| Banco de Dados II | 2026/1 | Plano de ensino |
| Business Intelligence e Data Visualization | 2026/1 | Plano de ensino, duas aulas em slides e dois textos (dashboards, KPIs e performance) |

## Big Data

**Caracterização pelos três Vs.** Volume: 4 arquivos CSV, 7,51 GB e 17.744.217 linhas
(AV3). Velocidade: lote anual, a fonte muda uma vez por edição do ENEM. Variedade: dado
estruturado (CSV) com dicionários em PDF e planilha, códigos que mudam de rótulo entre
edições (`docs/dicionario/`).

| Técnica | Usada? | Evidência ou justificativa |
| --- | --- | --- |
| Avaliar escala antes de escolher ferramenta | Sim | Benchmark de pandas, Polars, DuckDB e Spark sobre os dados reais (`docs/stack/`) |
| Spark / processamento distribuído | Medido e não adotado | Spark local levou de 4 a 5 vezes o tempo do DuckDB em dados que cabem numa máquina (AV3, seção 5.5). A disciplina orienta usar Spark quando há gargalo real; não havia. |
| ETL em lote | Sim | `scripts/etl.py`, RAW → TRUSTED → ANALYTICS |
| Arquitetura medalhão | Sim | RAW/TRUSTED/ANALYTICS correspondem a bronze/prata/ouro (`docs/modelagem/README.md`) |
| Formato colunar e compressão | Sim | Parquet com ZSTD, redução de 95,0% sobre o CSV, codec escolhido por medição (AV3, seção 5.5) |
| Particionamento | Sim | Por edição (`ano=<ano>`), com justificativa estatística medida na AV6 (`docs/av6/estatistica.md`, seção 7) |
| Streaming, ELT, carga incremental | Não | A fonte é estática e publicada uma vez por ano; carga completa com hash da fonte é suficiente e mais simples de auditar |
| NoSQL, grafos, bancos vetoriais | Não | Não há padrão de acesso que precise deles: o app lê distribuições inteiras uma vez |
| Lakehouse (Delta, Iceberg) | Não | Não há atualização, merge nem histórico de versões de tabela; a versão do dado é controlada por hash e manifesto |

## Engenharia de Dados e MLOps

| Técnica | Usada? | Evidência ou justificativa |
| --- | --- | --- |
| Produto de dados (problema, usuário, contrato de saída) | Sim | Plano de Trabalho; contrato em `docs/contrato/`; dicionário de indicadores em `docs/indicadores.md` (AV6) |
| Modelagem dimensional: grão, fato, dimensões | Sim (AV6) | `docs/modelagem/README.md`: frase do grão, medidas aditivas e semiaditivas, chave única conferida antes de publicar |
| Contratos entre camadas e qualidade | Sim | Contrato por coluna (`scripts/colunas.py`), funil sem perda silenciosa, conferência contra o profiling (AV3) |
| Escrita atômica e idempotência | Sim | Arquivo temporário substituído no fim; nova execução regera a partição inteira (AV3, seção 3.4) |
| Rastreabilidade e linhagem | Sim | Hash da fonte, manifestos da TRUSTED e da ANALYTICS com commit; `run_id` ligando os dois manifestos (AV6) |
| Barreira de qualidade antes de publicar | Sim (AV6) | `scripts/auditar_artefatos.py`; publicação só com saída 0 (DL-08) |
| CI | Sim | GitHub Actions: compilação, testes sintéticos, piso de privacidade e bloqueio de dado versionado |
| Data drift (KS, PSI) | Sim (AV6) | Drift entre edições medido com D de KS exato e PSI (`docs/av6/estatistica.md`, seção 7); serve de barreira para edições futuras |
| Classificação, matriz de confusão, desbalanceamento, SMOTE | Não | O produto não prevê nada: não há variável-alvo nem decisão categórica. O Plano de Trabalho exclui previsões, e o app diz que a posição "não prevê aprovação". |
| Árvores (Random Forest, XGBoost, LightGBM, CatBoost) | Não | Mesmo motivo: não há modelo preditivo |
| Séries temporais (ARIMA, SARIMA) | Não | São só quatro edições anuais, série curta demais para identificar tendência e sazonalidade; e as edições não são comparáveis entre si (drift medido na AV6) |
| MLOps de modelo (registro, CT, monitoramento de modelo) | Não se aplica | Não há modelo. Do ciclo de MLOps, o projeto aplica versionamento, CI, release por tag e monitoramento do serviço |

## Computação em Nuvem

Detalhamento em `docs/av6/nuvem.md`.

| Técnica | Usada? | Evidência ou justificativa |
| --- | --- | --- |
| Modelo de serviço PaaS | Sim | Replit, Reserved VM (DL-06, DL-08) |
| Responsabilidade compartilhada | Sim (AV6) | Matriz em `docs/av6/nuvem.md`, seção 2 |
| Planejamento de custo (CAPEX/OPEX, FinOps) | Sim (AV6) | Hipóteses e preços em `docs/av6/nuvem.md`, seção 6 |
| Dimensionamento por medição | Sim (AV6) | `scripts/medir_desempenho.py` no ambiente real |
| Segurança: dados fora do repositório, menor exposição | Sim | R1, projeto privado, `checar_saude.py` testa exposição (DL-09) |
| Monitoramento e resposta a incidentes | Sim (AV6) | Painel do Replit, monitor externo, tabela de incidentes |
| Backup, RPO e RTO | Sim (AV6) | `docs/av6/nuvem.md`, seção 7 |
| Docker | Não | O Replit monta o ambiente pelo `.replit`; o Dockerfile de `EVOLUCAO-FUTURA-NUVEM.md` é só um esboço não testado |
| IaaS (VM própria) | Não | Exigiria operar sistema, TLS e firewall para um app sem estado (`docs/av6/nuvem.md`, seção 1) |
| Serverless (FaaS) | Não | Streamlit mantém WebSocket e sessão; partida a frio prejudicaria a primeira consulta |
| PostgreSQL com volume persistente | Não | Não há dado transacional nem persistência do usuário (RNF04) |
| Rede virtual, sub-redes, NAT | Abstraído pela plataforma | Um único ponto de entrada HTTPS e nenhum serviço interno; fluxos em `docs/av6/nuvem.md`, seção 4 |
| Armazenamento de objetos | Não, com alternativa registrada | Artefatos como arquivos do projeto; Object Storage do Replit avaliado e descartado (`docs/av6/nuvem.md`, seção 5) |

## Estatística I (pela ementa)

Detalhamento em `docs/av6/estatistica.md`.

| Técnica prevista na ementa | Usada? | Evidência ou justificativa |
| --- | --- | --- |
| População e amostra | Sim | O produto usa a população de elegíveis; a AV6 mede o erro que uma amostra de 1% teria (seção 6) |
| Amostragem aleatória simples e estratificada | Sim (AV6, como análise) | Comparação das duas com 200 amostras; estratificar por UF não reduziu o erro |
| Medidas de tendência central | Sim | Média e mediana (DL-01); moda não exibida, com justificativa |
| Medidas de dispersão | Sim | Variância populacional, desvio-padrão, IQR (AV6) |
| Histograma | Sim | Faixas protegidas de pelo menos 100 pessoas |
| Boxplot | Sim (AV6) | Caixa protegida na página inicial, bigodes em P5/P95 |
| Distribuição normal | Sim (AV6, como análise) | Comparação de Φ(z) com o percentil exato: erro de até 8,6 pp |
| Binomial e Poisson | Não | Não há contagem de sucessos em ensaios nem eventos por intervalo no problema |
| Intervalos de confiança e testes de hipótese | Não, por decisão metodológica | As medidas são parâmetros da população, não estimativas; com milhões de participantes, qualquer teste daria p ≈ 0. O produto informa o tamanho do efeito (probabilidade de superioridade) |

## Banco de Dados II (pelo plano de 2026/1)

| Técnica prevista no plano | Usada? | Evidência ou justificativa |
| --- | --- | --- |
| Chaves e restrições de integridade | Sim, por código | Equivalentes de PK, CHECK e integridade entre tabelas em `auditar_artefatos.py` (`docs/modelagem/README.md`, seção 3) |
| Normalização | Avaliada e não aplicada | Camada analítica larga, lida por varredura, sem anomalias de atualização |
| Índices e particionamento | Equivalente físico | Partição por edição, Parquet colunar ordenado, busca binária em memória |
| Planos de execução | Sim (AV6) | `auditar_artefatos.py --explicar` mostra o EXPLAIN ANALYZE da consulta do app |
| Triggers e stored procedures | Não | Não há SGBD transacional |

## Business Intelligence e Data Visualization (2026/1)

| Técnica | Usada? | Evidência ou justificativa |
| --- | --- | --- |
| Pergunta e público antes do gráfico | Sim | Cada página abre com a pergunta do módulo |
| Contrato de KPI (fórmula, universo, N, unidade) | Sim (AV6) | `docs/indicadores.md` |
| Escolha do gráfico pela tarefa | Sim | Histograma e densidade para distribuição; dot plot para comparar medianas de 27 UFs (AV6); boxplot para quartis (AV6) |
| Integridade da escala (barras a partir de zero) | Sim (AV6) | O gráfico de medianas em barras truncadas virou dot plot |
| Cor com significado e acessível | Sim (AV6) | Papel fixo de cada cor; contraste de 3:1 e 4,5:1 nos dois temas conferido em teste |
| Fonte e atualização visíveis | Sim (AV6) | Rodapé com fonte, data da conferência e commit |
| Informação essencial fora do passar do mouse | Sim (AV6) | N das UFs no rótulo do eixo |
| SQL parametrizada | Sim (AV6) | `read_parquet(?)` no app |
| Cache | Sim | Dados públicos agregados, iguais para todos os usuários (sem risco de servir dado de um usuário a outro). No pente fino da AV6 os artefatos passaram de `st.cache_data`, que copiava até 37 MB a cada clique, para `st.cache_resource`, compartilhado e só de leitura: a página territorial caiu de 611 ms para 23 ms (`docs/qa/relatorio-qa-av6.md`) |
| Medição de desempenho p50/p95 | Sim (AV6) | `medir_desempenho.py`, `checar_saude.py` |
| Teste com público-alvo | Não, por decisão do PO (DL-10) | O protocolo está pronto (`docs/qa/teste-usabilidade.md`), mas não houve como recrutar pessoas de fora da equipe a tempo. Em parte, foi substituído por auditoria automática de acessibilidade (WCAG 2.1 AA) e avaliação heurística interna (`docs/qa/relatorio-qa-av6.md`), que não medem a compreensão de um usuário real |
| Metas, semáforos, alertas | Não | O produto descreve uma posição; não há meta nem ação esperada do usuário |
| Velocímetros e pizza | Não | O anel de posição mostra uma única proporção (o percentil, parte de 100%) e é acompanhado pelo valor em texto |
