# Apresentação AV2 — Radar ENEM (Equipe A)

Marco da Sprint 3 (29/09/2026): primeiro fluxo ponta a ponta, input -> consulta -> estatística -> visualização. Números conferidos em `docs/profiling/`, `docs/contrato/`, `docs/stack/` e no Plano de Trabalho.

## 1. Critérios de avaliação

| Critério | Peso | Onde é atendido |
| --- | --- | --- |
| Clareza e organização da apresentação | 20% | Sequência problema -> proposta -> plano x entregue -> demo -> próximos passos |
| Compreensão e descrição do problema do cliente | 20% | Slides 2 e 3 |
| Coerência da proposta de solução | 20% | Slides 4 a 6 |
| Evolução técnica em relação ao planejamento | 20% | Slides 7 a 9 e 11 |
| Demonstração prática das funcionalidades | 20% | Slide 10 (demo ao vivo) |

## 2. Roteiro por critério

### Problema do cliente

- O participante recebe as notas, mas não recebe contexto: uma nota de 620 em Matemática não diz se está acima ou abaixo de quem tem a mesma renda, quantas pessoas formam o grupo, nem como seria em 2019.
- A informação é pública, mas inacessível: 7,5 GB de CSV em latin-1, 17,7 milhões de linhas.
- 2019-2022 é o recorte da pandemia: abstenção de 23% (2019) para 51,5% (2020); inscritos caem 44% entre 2020 e 2021. As edições não são populações equivalentes.
- Ressalva: produto descritivo. Percentil não é probabilidade de aprovação; diferença entre grupos não é causa.

### Coerência da solução

| Restrição | Decisão | Evidência |
| --- | --- | --- |
| Web espera segundos; ler o CSV leva minutos | Lote offline (RAW -> TRUSTED -> ANALYTICS) e runtime que só consulta artefatos | ETL em ~1 min; percentil em 2 ms / 65 MB |
| Hospedagem gratuita com ~1 GB de RAM | DuckDB com `memory_limit` | Único motor abaixo de 1 GB em todas as consultas (pandas e Polars > 2 GB na `q3`) |
| Volume de 7,5 GB | 58 de 76 colunas, Parquet zstd | 22,6x menor que o CSV; TRUSTED com 340 MB |
| LGPD | Piso de 100 participantes; app só com agregados; notas digitadas não gravadas | `docs/privacidade.md`, `scripts/verificar_piso.py` |
| Comparabilidade | Elegível = presente nas 4 provas e não treineiro; exclusões contadas no funil | `docs/contrato/` |

### Evolução em relação ao planejamento

- Desvio justificado por medição: o plano previa Polars no ETL; o benchmark levou ao DuckDB (6 a 9 s por edição contra 8 a 15 s, lê latin-1 sem converter, Parquet ~20% menor).
- Spark foi medido, não descartado por princípio: 4 a 5 vezes mais lento.
- Entregue conforme o plano: hash SHA-256 da fonte, profiling, dicionário, contrato, funil sem perdas silenciosas, Parquet, benchmark, motor estatístico v0 (`percentil_faixas`, `histograma`), fluxo ponta a ponta, 13 testes com dados sintéticos, PRs revisados e mergeados.
- Ainda não feito (declarar):
  - POC de cloud (prevista na Sprint 1): deploy ainda não testado.
  - Design system: interface no visual padrão do Streamlit.
  - Média, desvio-padrão e Z-Score no resultado (RF02, Sprint 5).
  - Módulos autorais: Sprint 5 em diante, no prazo.
- Mudança de equipe: Guilherme Zamboni saiu; Guilherme Anselmo assumiu design/frontend e o módulo Rede de ensino de origem.

### Demonstração prática

1. `./scripts/verify_raw.sh`: hashes da fonte conferem.
2. Manifesto e funil do ETL (inscritos -> presentes -> elegíveis).
3. `./.venv/bin/streamlit run app/app.py`: edição 2022, MT 620 e Redação 800; mostrar percentil, gráfico com "sua nota", n do grupo e o bloco "Como a posição é calculada".
4. Trocar para 2020 com a mesma nota: o percentil muda (gancho do problema da pandemia).
5. `./.venv/bin/python -m unittest discover tests`: 13 testes passam.

Contingência: a demo é local (sem deploy). Gravar um vídeo curto antes e conferir que `data/analytics/dist_notas.parquet` existe na máquina que vai apresentar.

## 3. Divisão de fala

| Integrante | Slides |
| --- | --- |
| Samuel Silva de Rezende | 1, 2, 3, 11, 12 |
| Vinícius Joacir dos Anjos | 4, 7, 8, 9, 10 |
| Guilherme da Silva Anselmo | 5, 6 e os testes na demo |

## 4. Prompts para o gerador de slides

### Prompt de estilo (colar primeiro)

```
Crie uma apresentação acadêmica de 12 slides em português do Brasil, formato 16:9, para a AV2 do Projeto Aplicado III (Ciência de Dados e IA, UniSENAI/SC, Florianópolis). Projeto: "Radar ENEM", da Equipe A.

Estilo: limpo e técnico. Fundo branco, azul institucional (#2563eb) como cor principal, azul-claro (#93c5fd) de apoio e vermelho (#dc2626) só para destaques pontuais. Fonte sem serifa. No máximo 5 bullets por slide e frases curtas. Números em destaque grande quando forem o ponto do slide. Sem imagens genéricas de banco de fotos; prefira diagramas simples, tabelas e ícones lineares. Rodapé em todos os slides: "Radar ENEM · Equipe A · AV2 · 29/09/2026".

Não invente dados: use só os números que eu fornecer em cada slide.
```

### Slide 1 — Capa (Samuel)

```
Slide de capa.
Título: "Radar ENEM"
Subtítulo: "Diagnóstico estatístico comparativo com os Microdados do ENEM 2019–2022"
Linha menor: "AV2 · Sprint 3 · MVP ponta a ponta"
Equipe (3 nomes com o papel embaixo):
- Samuel Silva de Rezende: Líder / Product Owner
- Vinícius Joacir dos Anjos: Líder de Desenvolvimento e IA
- Guilherme da Silva Anselmo: QA, Validações e Segurança · Design e Frontend
Orientador: Gustavo Stangherlin Cantarelli
Centro Universitário SENAI SC, Campus Florianópolis.
```

### Slide 2 — O problema (Samuel)

```
Título: "A nota chega sem contexto"
Destaque central, em citação grande: "Uma nota de 620 em Matemática está acima ou abaixo de quem tem a mesma renda que eu? Quantas pessoas formam esse grupo? Como seria em 2019?"
Três bullets:
- O participante recebe as notas, mas não a posição relativa
- A resposta está nos microdados públicos do INEP...
- ...mas são 7,5 GB de CSV e 17,7 milhões de linhas: só quem programa consegue usar
Frase de fechamento: "O Radar ENEM encurta essa distância."
```

### Slide 3 — Por que 2019–2022 (Samuel)

```
Título: "O recorte é a pandemia"
Uma linha do tempo horizontal com 4 marcos:
- 2019: última edição pré-pandemia, abstenção de 23% no 1º dia
- 2020: escolas fechadas, abstenção de 51,5%
- 2021: inscritos caem para 3,1 milhões, o menor número desde 2005
- 2022: retomada, com a base ainda sem se recompor
Mensagem embaixo: "Mudou a nota e mudou quem fez a prova: as edições não são populações equivalentes."
Caixa de ressalva discreta: "Produto descritivo: percentil não é chance de aprovação, e diferença entre grupos não é prova de causa."
```

### Slide 4 — A proposta (Vinícius)

```
Título: "A solução: processar uma vez, consultar em milissegundos"
Diagrama horizontal de fluxo com 4 caixas e setas:
[RAW: CSV oficial do INEP + hash SHA-256] → [TRUSTED: 58 colunas tipadas + regra de elegibilidade] → [ANALYTICS: distribuições agregadas, grupos ≥ 100] → [App web: nota → percentil → gráfico]
Uma chave sob as três primeiras caixas: "offline, roda 1 vez (~1 min)"
Uma chave sob a última: "online, 1 GB de RAM, responde em ms"
Citação pequena: "Separação lote × consulta (Kleppmann, 2017)"
```

### Slide 5 — Fundação de dados, Sprint 1 (Anselmo)

```
Título: "Conhecer o dado antes de usar"
Tabela do funil de elegibilidade:
| Edição | Inscritos | Elegíveis |
| 2019 | 5.095.171 | 3.174.212 |
| 2020 | 5.783.109 | 2.242.169 |
| 2021 | 3.389.832 | 1.870.734 |
| 2022 | 3.476.105 | 1.927.753 |
Legenda da tabela: "Elegível = presente nas 4 provas e não treineiro. Toda exclusão é contada por motivo: nada é descartado em silêncio."
Coluna lateral com 4 ícones de entregas: Hash SHA-256 da fonte · Profiling das 4 edições · Dicionário harmonizado · Contrato de dados (58 de 76 colunas)
```

### Slide 6 — LGPD e ética (Anselmo)

```
Título: "Privacidade por construção"
Quatro cartões:
1. "Piso de 100": nenhum grupo com menos de 100 participantes é exibido
2. "Só agregados": o app nunca carrega dado individual
3. "Nada gravado": as notas digitadas vivem só na sessão e somem ao fechar a aba
4. "Verificável": script verificar_piso.py roda antes de cada Pull Request
Rodapé do slide: "Lei nº 13.709/2018 (LGPD) · RNF04 do Plano de Trabalho"
```

### Slide 7 — Benchmark da stack, Sprint 2 (Vinícius)

```
Título: "A stack foi decidida por medição, não por opinião"
Gráfico de barras horizontal: "Pico de memória na consulta mais pesada (4 edições, 2 núcleos)", com uma linha vertical vermelha tracejada em 1 GB, rotulada "limite da hospedagem gratuita":
- pandas: 2.044 MB
- Polars: 2.111 MB
- DuckDB: 497 MB (barra destacada em azul forte)
Três bullets ao lado:
- 5 motores testados nas 4 edições reais, sem amostragem
- DuckDB: o ETL mais rápido (6 a 9 s por edição)
- Só o DuckDB coube em 1 GB em todas as consultas
```

### Slide 8 — Plano × realizado (Vinícius)

```
Título: "O que mudou em relação ao plano, e por quê"
Tabela de 3 colunas (Camada | Hipótese do plano | Decisão final):
| ETL | Polars | DuckDB ✱ |
| Formato | Parquet ZSTD | Parquet ZSTD ✓ |
| Consulta | DuckDB | DuckDB ✓ |
| Interface | Streamlit + Plotly | Streamlit + Plotly ✓ |
| Spark | Só se necessário | Medido e não adotado ✓ |
Caixa destacada para a linha ✱: "O DuckDB foi mais rápido, lê o latin-1 do INEP sem converter e gera um Parquet ~20% menor. Um motor só no ETL e no runtime significa uma dependência a menos."
Frase final: "O plano previa validar a stack por benchmark; o benchmark mudou a decisão."
```

### Slide 9 — Números do ganho (Vinícius)

```
Título: "O efeito da arquitetura"
Três números gigantes lado a lado, cada um com uma legenda curta:
- "22,6×": Parquet zstd menor que o CSV (2019: 2,24 GB → 101 MB)
- "75%": do volume bruto descartado pelo contrato (colunas de respostas item a item)
- "2 ms": para calcular um percentil pela camada ANALYTICS, lendo 0,2 MB em vez de 340 MB
Linha embaixo: "Meta do RNF02: consultas em até 3 s. Atingida com folga no percentil."
```

### Slide 10 — Demonstração (Vinícius conduz, Anselmo roda os testes)

```
Título: "Demonstração ao vivo"
Slide quase vazio, com um mockup de navegador mostrando o app "Radar ENEM": um formulário com as 5 notas (CN, CH, LC, MT, Redação), um seletor de edição e um histograma azul com uma linha vermelha tracejada "sua nota".
Três passos numerados na lateral:
1. Informar a nota e escolher a edição
2. Ver o percentil, o gráfico e o tamanho do grupo comparado
3. Trocar 2022 → 2020 com a mesma nota: a posição muda
Nota pequena: "Qualidade: 13 testes automatizados com dados sintéticos"
```

Substituir o mockup por um print real do app antes de apresentar; o print também serve de backup se a demo falhar.

### Slide 11 — Próximos passos (Samuel)

```
Título: "O que vem agora"
Duas colunas.
Coluna "Pendências conhecidas":
- Deploy em nuvem (Streamlit Community Cloud ou Hugging Face Spaces) e medição de memória e latência reais
- Design system e identidade visual da interface
- Média, desvio-padrão e Z-Score no resultado (RF02)
Coluna "Próximas sprints":
- Sprint 4 (até 13/10): engenharia consolidada, quality report, AV3
- Sprint 5 (até 27/10): motor estatístico v1 e os 4 módulos autorais
- Sprint 6 (até 10/11): integração beta, acessibilidade, performance
Faixa embaixo com os 4 módulos: Equidade socioeconômica (Samuel) · Recorte territorial (Vinícius) · Capital escolar familiar (Anselmo) · Rede de ensino de origem (Anselmo)
Caixa pequena: "Mudança de equipe: com a saída de um integrante, Guilherme Anselmo assumiu design/frontend e o módulo Rede de ensino."
```

### Slide 12 — Encerramento

```
Título: "Obrigado! Perguntas?"
Subtítulo: "Radar ENEM: microdados públicos transformados em informação interpretável, com rigor estatístico e custo zero."
Linha menor: "Código, documentação e benchmark no GitHub do projeto"
Nomes da equipe em linha, discretos: Samuel Silva de Rezende · Vinícius Joacir dos Anjos · Guilherme da Silva Anselmo
```

## 5. Checklist antes de apresentar

- [ ] Conferir se o gerador manteve os números exatos (costuma arredondar ou inventar).
- [ ] Trocar o mockup do slide 10 por um print real do app.
- [ ] Gravar vídeo curto da demo como backup.
- [ ] Confirmar `data/analytics/dist_notas.parquet` na máquina da apresentação.
- [ ] Se faltar tempo: fundir o slide 3 com o 2 e o 9 com o 7.
