# Relatório de QA, segurança e otimização da AV6 (pente fino)

- **Data:** 24/11/2026
- **Responsável:** Samuel Silva de Rezende (Product Owner), que assumiu o pente fino por
  prazo (DL-10). Vinícius Joacir dos Anjos e Guilherme da Silva Anselmo revisam o PR.
- **Versão conferida:** `main` depois do PR #38 (identidade visual, `f2d6a92`), mais os
  commits deste pente fino.
- **Link público:** <https://radarenem-projetoaplicado3-kirasapiens.replit.app>

O objetivo foi conferir o produto inteiro antes do relatório final: o que o app faz,
quanto custa cada interação, o que fica exposto na internet e o que o CI barra antes
de publicar. Cada achado virou um commit com a medida de antes e depois.

## 1. Resumo

| Área | Achado | O que foi feito | Resultado |
| --- | --- | --- | --- |
| Otimização | Artefatos em `st.cache_data`: cópia de até 37 MB a cada clique e por sessão | `st.cache_resource` com o dado congelado (só leitura) | Execução da página territorial de 611 ms para 23 ms (1 CPU) |
| Otimização | Observador de arquivos ligado na publicação | `--server.fileWatcherType none` no `[deployment]` | Menos CPU e memória parados na VM de 0,5 vCPU |
| QA | Aviso `theme.*.base is not a valid config option` (Streamlit 1.66) | Linhas `base` removidas do `config.toml` | Aviso sumiu, visual igual |
| QA | Legenda "acima dessa porcentagem dos N participantes" ambígua | "parcela dos N participantes com nota menor que a sua, contando metade de quem tirou a mesma nota" (posto médio, como no cálculo) | Mesma definição em todas as páginas e igual à do cálculo |
| QA | CI só fazia `compileall` | ruff (F, E9, B) no CI; 21 apontamentos resolvidos | `zip(..., strict=True)` no PSI evita cálculo truncado |
| Segurança | Dependências sem auditoria automática | `pip-audit` no CI | Nenhuma vulnerabilidade conhecida |
| Segurança | XSRF e CORS só pelo padrão do Streamlit | Explícitos no `config.toml`; upload limitado a 1 MB | Cookie XSRF conferido no link público |
| Segurança | Revisão de QA do ADR-001 pendente desde 03/11 | Revisão feita, ação por ação (`docs/privacidade.md`) | Nenhum artefato baixável pelo link público |
| Operação | Monitor externo previsto no `nuvem.md`, mas nunca criado | Workflow agendado do GitHub Actions roda `checar_saude.py` no link a cada 3 horas | Disponibilidade e privacidade conferidas de fora do Replit, com histórico |
| Acessibilidade | Os dois logotipos sem texto alternativo (axe: crítico, 2 por página) | `alt` no `st.image` | 0 violações WCAG 2.1 AA nas 4 páginas, nos 2 temas, no computador e no celular |
| Usabilidade | Arcos decorativos passavam por trás do texto (celular e lado direito no computador) | Coluna de conteúdo com fundo opaco: arcos só nas margens | Texto sem interferência |
| Usabilidade | Primeira abertura mostrava "Running carregar()", texto técnico | Mensagem "Carregando os dados do ENEM..." | Linguagem do usuário |

## 2. Testes

| Medida | Valor |
| --- | --- |
| Testes automatizados | 282 (`python -m unittest discover -s tests`), todos passando |
| Cobertura do núcleo do produto (app, motor estatístico, três módulos, ETL e auditoria) | 95% das linhas (2.176 linhas, 119 sem execução) |
| Cobertura por página do app | Início 98%, Equidade 94%, Territorial 93%, Capital 95%, `ui.py` 97% |
| Cobertura do repositório inteiro | 58%: os scripts de uso único (benchmark da AV3, profiling, dicionário, contrato) e os que dependem de rede (`checar_saude.py`) não têm teste automatizado |
| Linter | `ruff check app scripts tests` sem apontamentos |

Medido com `coverage run --source=app,scripts -m unittest discover -s tests`.

Testes novos deste pente fino:

- `TestCacheSemCopia` (`tests/test_ui.py`): o dado em cache é só leitura em todos os
  níveis (o `congelar()` é recursivo e recusa tipos mutáveis desconhecidos, como arrays do
  numpy; revisão do #39), e nenhuma página volta a usar `cache_data` nos artefatos.
- `TestIdentidadeVisual` (PR #38): o CSS neon não carrega recurso externo, os arcos ficam
  só no fundo da página e os logotipos ficam fora de `app/static/`.
- `TestLogotiposAcessiveis` (`tests/test_ui.py`): os dois logotipos têm texto alternativo.

## 3. Otimização

### 3.1 Cache sem cópia

O `st.cache_data` devolve uma **cópia** do valor guardado (via pickle) a cada chamada.
Como cada clique reexecuta a página, a cópia acontecia em toda interação e em cada
sessão aberta ao mesmo tempo. Medido com os artefatos reais:

| Artefato | Tamanho em cache | Cópia por execução |
| --- | --- | --- |
| Recorte territorial | 37 MB | 515 ms |
| Capital escolar familiar | 9 MB | 155 ms |
| Equidade socioeconômica | 9 MB | 120 ms |

Com o `st.cache_resource`, todas as sessões leem o mesmo objeto. Para que nenhum código
o altere por engano (o que afetaria todos os visitantes), `ui.congelar()` transforma o
dicionário em `MappingProxyType` e cada lista em tupla.

Tempo de uma execução completa de cada página com o cache quente, medido com o
`AppTest` do Streamlit sobre os artefatos reais, com o processo limitado a 1 CPU
(`taskset -c 0`) para se aproximar da VM de 0,5 vCPU (mediana de 8 execuções):

| Página | Antes | Depois |
| --- | --- | --- |
| Início | 91 ms | 28 ms |
| Equidade socioeconômica | 160 ms | 21 ms |
| Recorte territorial | 611 ms | 23 ms |
| Capital escolar familiar | 138 ms | 29 ms |

O cálculo do percentil em si não mudou: continua o medido em `docs/deploy/replit.md`
(consulta p95 entre 70 e 416 ms no Shell do Replit). O que saiu foi o custo fixo de
copiar o artefato, pago antes de qualquer cálculo.

### 3.2 Publicação sem observador de arquivos

Na publicação o código não muda, então o observador de arquivos do Streamlit só ocupava
CPU e memória. O `[deployment]` do `.replit` passou a usar `--server.fileWatcherType none`.
O botão Run do editor continua com o observador, para o desenvolvimento.

## 4. Segurança

### 4.1 Dependências

`pip-audit -r requirements.txt` (base de vulnerabilidades do PyPI/OSV): nenhuma
vulnerabilidade conhecida em 24/11/2026. O passo entrou no CI para barrar o PR antes de
a dependência chegar ao filtro de pacotes do Replit, que já tinha recusado o Pillow 12.x
por CVE (PR #35). As versões continuam fixas no `requirements.txt` (PR #36).

**Quando o pip-audit apontar uma vulnerabilidade nova** (revisão do #39): o passo falha
em qualquer PR, mesmo sem relação com a dependência, porque a base de vulnerabilidades
muda sem mudança no repositório. O tratamento combinado é:

1. Atualizar a dependência para a versão corrigida num PR próprio (`fix(deps): ...`), com
   a suíte de testes passando, como no PR #35. É o caminho padrão.
2. Só se não houver versão corrigida, ou se a correção quebrar o app: acrescentar
   `--ignore-vuln <ID>` ao passo do workflow, com um comentário no YAML dizendo o motivo
   (por exemplo, a função vulnerável não é usada pelo app), a data e a data de revisão,
   e registrar a exceção no Decision Log. A exceção sai assim que a correção existir.
3. Os outros PRs abertos esperam o PR da dependência e fazem rebase; não se desliga o
   passo para destravar um PR.

### 4.2 Análise estática (bandit)

| Onde | Apontamento | Avaliação |
| --- | --- | --- |
| `app/ui.py` | `try/except/pass` (baixo) | Ignora só a falha do `st.page_link` fora do contexto multipágina (testes). Mantido |
| `scripts/auditar_artefatos.py`, `capital_escolar.py`, `territorial.py` | SQL montado com texto (médio, confiança baixa) | Falso positivo: os nomes de tabela e coluna são constantes do código; caminhos e valores vão como parâmetro. Nenhum script recebe entrada do visitante |
| `scripts/analises_av6.py`, `auditar_artefatos.py`, `medir_desempenho.py` | `subprocess` (baixo) | Só `git rev-parse HEAD`, com lista de argumentos fixa e sem shell |
| `scripts/analises_av6.py` | `random` (baixo) | Amostragem estatística com semente fixa, não criptografia |

O app não monta SQL com valores digitados: as consultas do `app/app.py` usam parâmetro
(`read_parquet(?)`), e as notas digitadas só entram em funções Python de cálculo.

### 4.3 Link público

Conferido no navegador em 24/11/2026:

- HTTPS com `Strict-Transport-Security: max-age=63072000; includeSubDomains`, emitido pelo
  Replit;
- cookie `_streamlit_xsrf` presente, ou seja, proteção XSRF ativa;
- `/data/analytics/dist_exata.parquet`, o mesmo caminho com `..` pelo servidor de
  estáticos e `/app/assets/radar-enem.jpg` devolvem a página do app (HTML, mesmo etag do
  index), nunca o arquivo;
- `checar_saude.py`: `artefatos_expostos` vazio em 19/11 e 24/11.

Risco residual aceito: o Streamlit não permite configurar `Content-Security-Policy` nem
`X-Frame-Options`. O app não tem login nem ação que altere dados, então o risco de uma
página de terceiros embutir o Radar ENEM é baixo.

### 4.4 Privacidade (ADR-001)

A revisão de QA do ADR-001, pendente desde 03/11, foi feita neste pente fino. A tabela
com cada ação prevista e como foi conferida está em `docs/privacidade.md`. Nada do que o
visitante digita é gravado (R6): as análises de visitantes e o widget de feedback do
Replit ficam desligados, e os erros mostram só o tipo da exceção.

## 5. Acessibilidade e usabilidade

O teste com pessoas do público-alvo não foi feito (seção 7). Para cobrir parte desse
risco, foram feitas duas verificações internas, que **não** medem se um usuário real
entende o resultado sozinho.

### 5.1 Auditoria automática de acessibilidade (axe-core)

Ferramenta: axe-core 4.14, regras dos níveis A e AA da WCAG 2.0 e 2.1, aplicada com o app
rodando sobre os artefatos reais e **depois** de uma comparação (Matemática 650), para que
o resultado também fosse auditado. Combinações: 4 páginas × 2 temas × 2 larguras de tela
(1.280 px e 375 px, a de um celular).

| Rodada | Violações |
| --- | --- |
| Antes | 2 por página, nas 16 combinações: imagem sem texto alternativo (`image-alt`, crítico), os dois logotipos do PR #38 |
| Depois do `alt` nos logotipos | **0** nas 16 combinações |

Limite da ferramenta: o axe não calcula contraste de texto sobre imagem de fundo. Isso foi
resolvido pelo desenho: os arcos não ficam mais atrás de texto (5.2), e o contraste das
cores de texto nos dois temas já é conferido em teste (`tests/test_ui.py`, AV6).

### 5.2 Avaliação heurística interna (heurísticas de Nielsen)

Feita pelo PO, percorrendo as 4 páginas no computador e no celular, nos dois temas.
Gravidade de 0 (não é problema) a 4 (catastrófico).

| Heurística | Observação | Gravidade | Ação |
| --- | --- | --- | --- |
| 1. Visibilidade do estado do sistema | Na primeira abertura depois de publicar, aparecia "Running carregar()" por alguns segundos | 2 | Mensagem trocada por "Carregando os dados do ENEM..." |
| 2. Correspondência com o mundo real | Visão simples em frequência natural ("cerca de 76 em cada 100"); a legenda dos cartões dizia "acima dessa porcentagem", ambígua | 2 | Legenda unificada: "parcela dos N participantes com nota menor que a sua, contando metade de quem tirou a mesma nota" (posto médio, como no cálculo) |
| 3. Controle e liberdade do usuário | Campos com botão de limpar, edição e navegação sempre disponíveis | 0 | — |
| 4. Consistência e padrões | Mesmo formulário, mesma ordem de áreas e mesmo rodapé nas 4 páginas | 0 | — |
| 5. Prevenção de erros | Notas limitadas de 0 a 1.000 no próprio campo; a página só compara com ao menos uma nota | 0 | — |
| 6. Reconhecer em vez de lembrar | UF com sigla e nome; faixas de renda e escolaridade com o texto do questionário | 0 | — |
| 7. Flexibilidade e eficiência | Visão simples para leigos e visão técnica para quem quer os números | 0 | — |
| 8. Estética e design minimalista | Os arcos decorativos passavam por trás do texto do resultado no celular e na lateral direita no computador | 2 | Coluna de conteúdo com fundo opaco; os arcos ficam só nas margens |
| 9. Reconhecer, diagnosticar e corrigir erros | Mensagens de entrada inválida em português, sem detalhe técnico (`showErrorDetails = "type"`) | 0 | — |
| 10. Ajuda e documentação | "Como a comparação é feita" em cada página; fonte e data no rodapé | 0 | — |

As telas foram conferidas também com 375 px de largura: formulário em uma coluna, cartões
de resultado empilhados e nenhum texto cortado.

## 6. Operação: monitor externo

O `docs/av6/nuvem.md` previa um monitor externo de disponibilidade (UptimeRobot, por
exemplo), que nunca chegou a ser criado. O workflow `.github/workflows/monitor-producao.yml`
cumpre esse papel sem serviço de terceiros: a cada 3 horas, o GitHub Actions roda
`scripts/checar_saude.py` contra o link público, de fora do Replit, e o job falha se o app
não responder (código 1) ou se algum artefato puder ser baixado (código 2, ADR-001). O
resumo de cada execução fica na aba Actions, que vira o histórico de disponibilidade da
aplicação em nuvem. O workflow só faz GET de leitura e não usa segredos.

Dois cuidados de operação (revisão do #39):

- O GitHub desativa workflows agendados depois de 60 dias sem atividade no repositório.
  Se o projeto ficar parado depois da banca, o monitor para sem aviso; para reativar,
  basta abrir a aba Actions, escolher "Monitor da publicação" e clicar em "Enable
  workflow" (ou fazer qualquer commit). Se o link for desligado depois da banca, o
  monitor deve ser desativado junto, para não falhar todo dia.
- Os dois workflows usam `actions/checkout@v5` e `actions/setup-python@v6`, que rodam em
  Node.js 24; as versões anteriores geravam o aviso de descontinuação do Node.js 20.

## 7. Publicação

| Data | O que foi publicado | Saúde pela rede (p95) | Artefatos expostos |
| --- | --- | --- | --- |
| 19/11/2026 | Beta (`v1.0-beta`) | health 764 ms; página 582 ms; 0 falhas em 40 | nenhum |
| 24/11/2026 | Identidade visual (PR #38) | health 732 ms; página 593 ms; 0 falhas em 40 | nenhum |

A publicação deste pente fino vem depois do merge, pelo mesmo procedimento
(`docs/deploy/replit.md`), com nova checagem de saúde.

## 8. O que não foi feito

Decisões do PO em 24/11/2026 (DL-10):

- **Teste de usabilidade com o público-alvo** (`docs/qa/teste-usabilidade.md`): não houve
  como recrutar 3 a 5 pessoas de fora da equipe a tempo da entrega. O protocolo fica
  pronto para uma próxima versão. A auditoria de acessibilidade e a avaliação heurística
  (seção 5) cobrem parte do risco, mas não medem a compreensão de um usuário real.
- **RTO medido:** recriar a publicação do zero exigiria apagar o projeto no Replit às
  vésperas da entrega. Fica o tempo medido da republicação, cerca de 3 min do clique ao
  app no ar (24/11), e a estimativa documentada em `docs/av6/nuvem.md`, seção 7: de 30 a
  60 minutos, somando a importação do GitHub, o envio dos 5 artefatos (cerca de 13 MB) e a
  configuração da Reserved VM, passos manuais descritos em `docs/deploy/replit.md`.
- **Cabeçalhos CSP e X-Frame-Options:** fora do alcance do Streamlit (seção 4.3).
