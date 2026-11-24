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
| QA | Legenda "acima dessa porcentagem dos N participantes" ambígua | "parcela dos N participantes com nota menor que a sua" | Mesma definição em todas as páginas |
| QA | CI só fazia `compileall` | ruff (F, E9, B) no CI; 21 apontamentos resolvidos | `zip(..., strict=True)` no PSI evita cálculo truncado |
| Segurança | Dependências sem auditoria automática | `pip-audit` no CI | Nenhuma vulnerabilidade conhecida |
| Segurança | XSRF e CORS só pelo padrão do Streamlit | Explícitos no `config.toml`; upload limitado a 1 MB | Cookie XSRF conferido no link público |
| Segurança | Revisão de QA do ADR-001 pendente desde 03/11 | Revisão feita, ação por ação (`docs/privacidade.md`) | Nenhum artefato baixável pelo link público |

## 2. Testes

| Medida | Valor |
| --- | --- |
| Testes automatizados | 279 (`python -m unittest discover -s tests`), todos passando |
| Cobertura do núcleo do produto (app, motor estatístico, três módulos, ETL e auditoria) | 95% das linhas (2.166 linhas, 119 sem execução) |
| Cobertura por página do app | Início 98%, Equidade 94%, Territorial 93%, Capital 95%, `ui.py` 97% |
| Cobertura do repositório inteiro | 58%: os scripts de uso único (benchmark da AV3, profiling, dicionário, contrato) e os que dependem de rede (`checar_saude.py`) não têm teste automatizado |
| Linter | `ruff check app scripts tests` sem apontamentos |

Medido com `coverage run --source=app,scripts -m unittest discover -s tests`.

Testes novos deste pente fino:

- `TestCacheSemCopia` (`tests/test_ui.py`): o dado em cache é só leitura, e nenhuma página
  volta a usar `cache_data` nos artefatos.
- `TestIdentidadeVisual` (PR #38): o CSS neon não carrega recurso externo, os arcos ficam
  só no fundo da página e os logotipos ficam fora de `app/static/`.

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

## 5. Publicação

| Data | O que foi publicado | Saúde pela rede (p95) | Artefatos expostos |
| --- | --- | --- | --- |
| 19/11/2026 | Beta (`v1.0-beta`) | health 764 ms; página 582 ms; 0 falhas em 40 | nenhum |
| 24/11/2026 | Identidade visual (PR #38) | health 732 ms; página 593 ms; 0 falhas em 40 | nenhum |

A publicação deste pente fino vem depois do merge, pelo mesmo procedimento
(`docs/deploy/replit.md`), com nova checagem de saúde.

## 6. O que não foi feito

- **Teste de usabilidade com o público-alvo** (`docs/qa/teste-usabilidade.md`): depende
  de 3 a 5 pessoas de fora da equipe. Situação registrada no relatório final.
- **RTO (recriar a publicação do zero):** exigiria apagar e recriar o projeto no Replit.
  A referência medida é a republicação: cerca de 3 min do clique ao app no ar (24/11).
  Recriar do zero soma a importação do GitHub e o envio dos 5 artefatos (cerca de 13 MB),
  seguindo `docs/deploy/replit.md`.
- **Cabeçalhos CSP e X-Frame-Options:** fora do alcance do Streamlit (seção 4.3).
