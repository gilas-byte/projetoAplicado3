#C Implantação em nuvem, QA, segurança e operação | Hospedagem, garantia de qualidade, otimização e resposta a incidentes

## Escolha do provedor

O Plano de Trabalho previa uma prova de conceito em nuvem na Sprint 1 e deixava o provedor em aberto; o relatório da AV3 citava o Azure apenas como exemplo. A decisão foi tomada em 03/11/2026 e registrada na DL-06, com quatro critérios. O mais importante foi a privacidade dos artefatos: as CDFs têm frequências por nota que podem ser menores que 100 e só podem ficar no backend (ADR-001). Plataformas que publicam a partir de um repositório, como o Streamlit Community Cloud e o Hugging Face Spaces, citadas na AV2, exigiriam colocar os artefatos no Git, o que a regra R1 proíbe, ou buscá-los em outro armazenamento, com credencial e código a mais. O Replit aceita arquivos fora do Git dentro de um projeto privado, que ficam só no backend.

Quadro: Alternativas de hospedagem consideradas
Larguras: 22,40,38
| Alternativa | Vantagem | Por que não foi escolhida |
| --- | --- | --- |
| Streamlit Community Cloud | Gratuita, integrada ao Streamlit | Publica a partir do repositório: os artefatos teriam de ir para o Git ou vir de armazenamento externo |
| Hugging Face Spaces | Gratuita, com contêiner | Mesmo problema de publicação a partir do repositório |
| Azure (citado na AV3) | Controle completo e ampla oferta de serviços | Mais configuração e custo fora do plano já pago pelo PO |
| **Replit (escolhido)** | Arquivos fora do Git num projeto privado, PaaS, plano Core do PO já pago | Dependência de uma conta pessoal; ambiente compartilhado mais lento que o local, o que exigiu medição |
Fonte: DL-06 (`docs/decisoes/README.md`).

A DL-06 tratou o Replit como teste, com a troca de provedor como saída se algum critério falhasse. Em 16/11, sem tempo para avaliar outro provedor e com o relatório final exigindo o link público, a DL-08 tornou o Replit a hospedagem definitiva, com uma publicação beta para medir no ambiente real. A beta foi ao ar em 19/11/2026, às 00:10 (horário de Brasília), e nenhum critério de revisão da DL-06 foi atingido: o projeto ficou privado, nenhuma consulta passou de 3 s e o custo coube nos créditos do plano.

## Modelo de serviço e de implantação

O Replit é usado como **plataforma como serviço (PaaS)**, em **nuvem pública**. A equipe entrega o código e a configuração (`.replit`); a plataforma fornece o sistema operacional, o runtime Python, a rede, o certificado TLS e a execução contínua. O tipo de publicação é a **Reserved VM compartilhada**, com 0,5 vCPU e 2 GB de memória (máquina `e2-small`), sempre ligada, na região South America.

- **Por que PaaS e não IaaS.** Uma máquina virtual própria exigiria da equipe atualizar o sistema, configurar firewall e TLS, garantir reinício automático e montar monitoramento, tudo para uma aplicação sem estado que lê cinco arquivos pequenos. O PaaS transfere essa operação ao provedor. O PaaS é a escolha natural para uma aplicação web que segue o padrão da plataforma e quer reduzir administração.
- **Por que não *serverless* (FaaS).** O Streamlit mantém uma conexão WebSocket e o estado da sessão de cada usuário durante a visita. Funções *serverless* têm execução curta e sem estado, e a partida a frio afetaria a primeira consulta. FaaS é indicado para operações curtas orientadas a evento, o que não é o caso.
- **Por que Reserved VM e não Autoscale.** O Autoscale desliga a instância sem acesso e a recria na primeira visita. A primeira abertura do Recorte territorial carrega 2,2 milhões de linhas; para a banca e para quem abrir o link do relatório, a resposta precisa ser imediata. O custo da instância sempre ligada está na seção 6.8.

## Responsabilidade compartilhada

Quadro: Matriz de responsabilidade compartilhada da publicação
Larguras: 34,16,50
| Camada | Quem cuida | Como |
| --- | --- | --- |
| Hardware, rede física e virtualização | Replit | Plataforma |
| Sistema operacional e runtime Python | Replit | Ambiente Nix do Replit, `modules = ["python-3.12"]` no `.replit` |
| TLS (HTTPS) e domínio `*.replit.app` | Replit | Automático na publicação, com HSTS |
| Disponibilidade da instância | Replit | Reserved VM sempre ligada |
| Código da aplicação | Equipe | GitHub (`main`), importado pelo Replit |
| Dependências | Equipe | `requirements.txt` com versões fixas e auditadas no CI |
| Dados publicados (artefatos da ANALYTICS) | Equipe | Enviados ao projeto privado e conferidos por `auditar_artefatos.py` |
| Privacidade (piso, CDF só no backend, não persistência) | Equipe | Regras R1 a R7, ADR-001, DL-04 item 8 |
| Acesso à conta e ao projeto | Equipe (PO) | Conta pessoal do PO, projeto privado |
| Monitoramento e resposta a incidentes | Equipe, com ferramentas do Replit | Seção 6.12 |
Fonte: `docs/av6/nuvem.md`, seção 2.

A plataforma não assume a privacidade dos dados nem a correção do que é publicado. Essas responsabilidades continuam com a equipe, como prevê o modelo de responsabilidade compartilhada.

## Comparação com uma arquitetura de referência em nuvem

Uma arquitetura de referência para uma aplicação como o Radar ENEM teria aplicação Python em Docker, PostgreSQL com volume persistente e rede virtual com sub-redes pública e privada. O produto entregue não usa todos esses componentes, e cada ausência tem justificativa.

Quadro: Arquitetura de referência e o que foi adotado
Larguras: 24,18,58
| Componente da referência | No Radar ENEM | Justificativa |
| --- | --- | --- |
| Docker | Não usado | O Replit monta o ambiente a partir do `.replit` e do `requirements.txt`. O esboço de Dockerfile da AV3 nunca foi construído e fica como alternativa de portabilidade |
| PostgreSQL | Não usado | Não há entidade transacional: nenhum cadastro, login ou gravação, e o RNF04 proíbe persistir o que o usuário digita. Os dados são distribuições agregadas, somente leitura, que cabem em 12,6 MB e são lidas em memória |
| Rede virtual, sub-redes, NAT e grupos de segurança | Abstraído pela plataforma | Há um único ponto de entrada público (HTTPS do Replit) e nenhum serviço interno a isolar: não existe banco, fila ou API separada |
| Armazenamento de objetos para os microdados | Fora da nuvem | O RAW (7,5 GB) e a TRUSTED ficam na máquina da equipe; o ETL roda offline e só os agregados sobem |
| Função *serverless* de processamento | Não usada | O processamento pesado já é offline, em lote (seção 6.2) |
Fonte: `docs/av6/nuvem.md`, seção 3.

O que o produto mantém da referência é o princípio de **separar o ciclo de vida dos dados do ciclo de vida da aplicação**: o código vem do GitHub, por PR revisado; os dados vêm do pipeline, com hash conferido, e nunca entram no repositório.

## Fluxos de rede e armazenamento

Quadro: Fluxos de rede da aplicação publicada
Larguras: 22,24,22,32
| Origem | Destino | Protocolo e porta | Justificativa |
| --- | --- | --- | --- |
| Navegador do usuário | Proxy do Replit (`*.replit.app`) | HTTPS 443 e WebSocket seguro | Único acesso público |
| Proxy do Replit | Processo Streamlit na VM | HTTP 8501 interno (mapeado para a porta externa 80 no `.replit`) | Encaminhamento da plataforma; a 8501 não fica exposta |
| Processo Streamlit | `data/analytics/*.parquet` | Leitura local | Nenhum acesso de rede para os dados |
| Aplicação | Serviços de terceiros | Nenhum | Sem telemetria, fontes ou scripts externos |
| Monitor externo (GitHub Actions) | `/_stcore/health` e página inicial | HTTPS 443 | Só lê o estado e tenta baixar artefatos, o que deve falhar |
Fonte: `docs/av6/nuvem.md`, seção 4, e `.github/workflows/monitor-producao.yml`.

Quadro: Armazenamento de cada tipo de dado
Larguras: 24,26,26,24
| Dado | Tipo de armazenamento | Onde | Retenção e cópia |
| --- | --- | --- | --- |
| Código | Repositório Git | GitHub (`main`) e cópia no projeto do Replit | Histórico completo no GitHub |
| Artefatos da ANALYTICS (5 arquivos, 12,6 MB) | Arquivo no disco do projeto, incluído na publicação | Projeto privado, `data/analytics/` | Cópia de referência com o PO; hashes em `docs/deploy/artefatos.sha256` |
| Microdados (RAW) e TRUSTED | Arquivo local | Máquina da equipe | Hash dos zips em `data/raw/hashes.sha256` |
| Dados digitados pelo usuário | Nenhum | Só na memória da sessão | Não persistidos (R6) |
Fonte: `docs/av6/nuvem.md`, seção 5.

A publicação do Replit é uma cópia congelada do projeto no momento do clique em *Publish*. Arquivos gravados pela aplicação durante a execução se perderiam a cada nova publicação, o que não afeta o Radar ENEM, que não grava nada. O Object Storage do Replit permitiria trocar artefatos sem republicar, mas exigiria código de download na inicialização e uma credencial, para arquivos que mudam no máximo uma vez por edição do ENEM; por isso ficou de fora.

## Procedimento de publicação e atualização

O procedimento completo está em `docs/deploy/replit.md`. A primeira publicação seguiu dez passos: importar o repositório do GitHub; marcar o projeto como privado; enviar os cinco artefatos para `data/analytics/`; rodar a auditoria no Shell do Replit (barreira de qualidade); testar no editor; publicar como Reserved VM com monitoramento ligado; abrir as quatro páginas para aquecer o cache; conferir saúde e privacidade pela rede com `checar_saude.py`; medir no ambiente real com `medir_desempenho.py`; registrar o link.

O agente de IA do Replit foi usado só para configurar a publicação, com um prompt fechado escrito pela equipe e versionado (`docs/deploy/prompt-agente-replit.md` e `prompt-agente-republicar.md`), e com a proibição explícita de alterar código do produto (DL-08, item 4). Qualquer mudança de código entra por PR no GitHub, com revisão.

Para atualizar o código publicado, a `main` do Replit tem de ficar idêntica à do GitHub, sem commits próprios. O procedimento usado em 24/11 guarda eventuais commits locais numa branch de backup, traz a `main` do GitHub (`git fetch origin` e `git reset --hard origin/main`, que o Replit exige autorizar com `DANGEROUSLY_ALLOW_GIT=1`), roda auditoria e testes, reinicia o processo do editor (o Streamlit não recarrega um módulo já importado) e publica. Nunca se faz push nem "Sincronizar alterações" a partir do Replit: o GitHub só recebe mudanças por PR.

Quadro: Histórico de publicações
Larguras: 18,34,24,24
| Data | O que foi publicado | Tempo do clique ao app no ar | Verificação depois de publicar |
| --- | --- | --- | --- |
| 18/11/2026, 18:40 | Primeira tentativa | Bloqueada pela verificação de segurança antes de ir ao ar | Correção pelo PR #36 |
| 19/11/2026, 00:10 | Beta (`v1.0-beta`), três módulos e nova interface | Cerca de 8 min | Saúde p95: health 764 ms, página 582 ms, 0 falhas em 40; nenhum artefato exposto |
| 24/11/2026, 10:59 | Identidade visual (PR #38) | Cerca de 3 min | Saúde p95: health 732 ms, página 593 ms, 0 falhas em 40; nenhum artefato exposto |
Fonte: logs da publicação no Replit, `docs/deploy/replit.md` e `docs/qa/relatorio-qa-av6.md`, seção 7.

## Incidentes da implantação e como foram resolvidos

A implantação concentrou na última sprint a descoberta de restrições da plataforma. Os incidentes e as respostas foram registrados à medida que ocorreram.

Quadro: Incidentes da implantação
Larguras: 30,34,36
| Incidente | Causa | Resposta |
| --- | --- | --- |
| Instalação recusada com erro 403 (18/11) | O filtro de pacotes do Replit recusou o Pillow 12.x, exigido pelo Streamlit 1.64, por uma vulnerabilidade crítica (CVE-2026-112900, CVSS 9,2) | Streamlit 1.66.1 e Pillow 13.0.0, testados com toda a suíte (PR #35). O filtro não foi contornado |
| Publicação bloqueada pela verificação de segurança (18/11) | A verificação lê os manifestos e supõe versões vulneráveis para dependências indiretas não fixadas (anyio, certifi, h11 e idna) | Dependências indiretas fixadas nas versões instaladas e testadas e `setuptools` fixado no arquivo do benchmark (PR #36) |
| Correção automática do Centro de segurança criou um commit local no Replit | O PO acionou "Corrigir tudo com Agent" | O commit local não foi enviado ao GitHub; a mesma mudança entrou pelo PR #36, com revisão |
| `nodejs-24` acrescentado ao `.replit` | A automação de navegador do agente instalou o Node.js no projeto | Mudança descartada pelo painel Git, linha a linha, antes de publicar; o prompt passou a proibir Node.js |
| Editor mostrando a versão antiga depois de atualizar o código (24/11) | O processo do Run continuava com o `ui.py` antigo em memória | Reiniciar o Run passou a ser passo obrigatório do procedimento |
| Testes locais falhando com `TypeError` no `st.image` (24/11) | Ambiente local com o Streamlit 1.64; o parâmetro `alt` só existe no 1.66 | Ambiente reinstalado pelo `requirements.txt` (282 testes passando); o CI já usava a versão fixada |
Fonte: DL-08, `docs/deploy/replit.md` e descrições dos PRs #35, #36 e #39.

Os incidentes mostram o valor de duas práticas: versões fixas no `requirements.txt`, que tornam a instalação reproduzível e auditável, e a regra de que o GitHub é a única fonte do código, que impediu que uma correção automática da plataforma entrasse no produto sem revisão.

## Custo

Quadro: Hipóteses de custo da hospedagem
Larguras: 34,36,30
| Item | Hipótese | Valor |
| --- | --- | --- |
| Reserved VM compartilhada (0,5 vCPU, 2 GB) | Sempre ligada | US$ 0,0208 por hora, cerca de US$ 15 por mês |
| Período até a banca | 19/11 a 01/12/2026 | Cerca de 290 h, cerca de US$ 6 |
| Transferência de dados | Uso acadêmico, poucas dezenas de visitas | Desprezível frente à VM |
| Armazenamento | 12,6 MB de artefatos | Desprezível |
| Créditos mensais do plano Core do PO | Abatem o custo da publicação | Conferidos no painel de cobrança |
Fonte: documentação de preços do Replit consultada em 16/11/2026 (`docs/av6/nuvem.md`, seção 6); preços sujeitos a mudança.

Não há investimento de capital (CAPEX): nenhum servidor foi comprado. A despesa operacional (OPEX) é a máquina virtual. O Autoscale custaria menos com pouco acesso, mas com partida a frio; uma VM dedicada de 1 vCPU e 4 GB daria folga de memória por cerca de US$ 35 por mês e ficou registrada como primeira resposta se a memória ou o tempo de resposta ultrapassassem os limites (DL-08, item 5), o que não aconteceu. Os controles de custo adotados foram conferir o painel de cobrança semanalmente, usar o agente do Replit só com prompt fechado e conferir os créditos antes e depois de cada uso, e decidir depois da banca entre manter o link ou desligar a publicação, com nova entrada no Decision Log.

## Garantia de qualidade

Depois da beta, faltavam o QA da aplicação completa, a revisão de segurança, a otimização e a acessibilidade. Pelo prazo, o PO executou esse pente fino e os outros dois integrantes ficaram com a revisão do PR (DL-10). O PR #39 foi revisado por Vinícius Joacir dos Anjos, que pediu quatro ajustes, todos atendidos antes da aprovação e do merge em 24/11/2026: a legenda do percentil passou a dizer que quem tirou a mesma nota conta pela metade, como no cálculo; o congelamento do cache ficou recursivo e passou a recusar tipos mutáveis desconhecidos; a regra para vulnerabilidade nova no `pip-audit` foi documentada; e foi registrado que o GitHub desativa o monitor agendado depois de 60 dias sem atividade. O objetivo foi conferir o produto inteiro antes deste relatório: o que a aplicação faz, quanto custa cada interação, o que fica exposto na internet e o que o CI barra antes de publicar. Cada achado virou um commit com a medida de antes e depois, no PR #39, e o relatório completo está em `docs/qa/relatorio-qa-av6.md`.

Quadro: Achados do pente fino da AV6
Larguras: 14,32,30,24
| Área | Achado | O que foi feito | Resultado |
| --- | --- | --- | --- |
| Otimização | Artefatos em `st.cache_data`: cópia de até 37 MB a cada clique e por sessão | `st.cache_resource` com o dado congelado | Página territorial de 611 ms para 23 ms |
| Otimização | Observador de arquivos ligado na publicação | `--server.fileWatcherType none` na publicação | Menos CPU e memória parados na VM |
| QA | Aviso de configuração de tema inválida no Streamlit 1.66 | Linhas `base` removidas do `config.toml` | Aviso eliminado, visual igual |
| QA | Legenda ambígua dos cartões de percentil | "parcela dos N participantes com nota menor que a sua, contando metade de quem tirou a mesma nota" | Mesma definição em todas as páginas e igual à do cálculo |
| QA | CI só compilava o código | Linter ruff (F, E9, B) no CI; 21 apontamentos resolvidos | `zip(..., strict=True)` no PSI evita cálculo truncado |
| Segurança | Dependências sem auditoria automática | `pip-audit` no CI | Nenhuma vulnerabilidade conhecida |
| Segurança | XSRF e CORS só pelo padrão do framework | Explícitos no `config.toml`; envio de arquivos limitado a 1 MB | Cookie de proteção XSRF conferido no link público |
| Segurança | Revisão de QA do ADR-001 pendente desde 03/11 | Revisão feita, ação por ação | Nenhum artefato baixável pelo link público |
| Operação | Monitor externo previsto, mas não criado | Workflow agendado no GitHub Actions | Disponibilidade e privacidade conferidas de fora, a cada 3 h |
| Acessibilidade | Logotipos sem texto alternativo (axe: crítico) | `alt` nas imagens | 0 violações WCAG 2.1 AA em 16 combinações |
| Usabilidade | Arcos decorativos atrás do texto | Coluna de conteúdo com fundo opaco | Texto sem interferência |
| Usabilidade | "Running carregar()" na primeira abertura | "Carregando os dados do ENEM..." | Linguagem do usuário |
Fonte: `docs/qa/relatorio-qa-av6.md`, seção 1.

Quadro: Indicadores de qualidade do código na versão final
Larguras: 50,50
| Medida | Valor |
| --- | --- |
| Testes automatizados | 282, todos passando (`python -m unittest discover -s tests`) |
| Cobertura do núcleo (app, motor, três módulos, ETL e auditoria) | 95% das linhas (2.176 linhas, 119 sem execução) |
| Cobertura por página do app | Início 98%, Equidade 94%, Territorial 93%, Capital 95%, `ui.py` 97% |
| Cobertura do repositório inteiro | 58% (scripts de uso único e dependentes de rede sem teste) |
| Linter (ruff, regras F, E9 e B) | Sem apontamentos |
| Auditoria de dependências (pip-audit) | Nenhuma vulnerabilidade conhecida em 24/11/2026 |
| Verificação de acessibilidade (axe-core 4.14, WCAG 2.0 e 2.1 A e AA) | 0 violações em 16 combinações |
Fonte: `docs/qa/relatorio-qa-av6.md`, seção 2; cobertura medida com `coverage run --source=app,scripts -m unittest discover -s tests`.

### O que não foi feito, por decisão do PO

Duas verificações previstas não foram feitas, e a decisão foi registrada antes da entrega (DL-10, 24/11/2026):

- **Teste de usabilidade com o público-alvo.** Não houve como recrutar de três a cinco pessoas de fora da equipe a tempo. O protocolo fica pronto para uma próxima versão. A auditoria de acessibilidade e a avaliação heurística cobrem parte do risco, mas não medem a compreensão de um usuário real.
- **Tempo de recuperação (RTO) medido.** Recriar a publicação do zero exigiria apagar o projeto no Replit às vésperas da entrega. Fica o tempo medido da republicação (cerca de 3 min) e a estimativa documentada na seção 6.12.

## Otimização

### Cache sem cópia

O `st.cache_data` devolve uma cópia do valor guardado, via pickle, a cada chamada. Como cada clique reexecuta a página, a cópia acontecia em toda interação e em cada sessão aberta ao mesmo tempo. O custo foi medido com os artefatos reais.

Quadro: Custo da cópia do cache por artefato
Larguras: 40,30,30
| Artefato | Tamanho em cache | Cópia por execução |
| --- | --- | --- |
| Recorte territorial | 37 MB | 515 ms |
| Capital escolar familiar | 9 MB | 155 ms |
| Equidade socioeconômica | 9 MB | 120 ms |
Fonte: `docs/qa/relatorio-qa-av6.md`, seção 3.1.

Com o `st.cache_resource`, todas as sessões leem o mesmo objeto, congelado para que nenhum código o altere por engano (seção 4.13). O tempo de uma execução completa de cada página com o cache quente foi medido com o `AppTest` do Streamlit sobre os artefatos reais, com o processo limitado a um núcleo (`taskset -c 0`) para se aproximar da VM de 0,5 vCPU, como mediana de oito execuções.

Quadro: Tempo de execução de cada página antes e depois do cache sem cópia
Larguras: 40,30,30
| Página | Antes | Depois |
| --- | --- | --- |
| Início | 91 ms | 28 ms |
| Equidade socioeconômica | 160 ms | 21 ms |
| Recorte territorial | 611 ms | 23 ms |
| Capital escolar familiar | 138 ms | 29 ms |
Fonte: `docs/qa/relatorio-qa-av6.md`, seção 3.1.

O cálculo do percentil não mudou; o que saiu foi o custo fixo de copiar o artefato, pago antes de qualquer cálculo. O efeito é maior com vários visitantes ao mesmo tempo, porque cada sessão deixava de manter a própria cópia.

### Publicação sem observador de arquivos

Na publicação o código não muda, então o observador de arquivos do Streamlit só ocupava CPU e memória. A configuração de publicação passou a usar `--server.fileWatcherType none`; o botão Run do editor continua com o observador, para o desenvolvimento.

## Segurança

### Dependências

O `pip-audit`, sobre a base de vulnerabilidades do PyPI e do OSV, não encontrou vulnerabilidade conhecida nas dependências em 24/11/2026. O passo entrou no CI para barrar o PR antes de a dependência chegar ao filtro de pacotes do Replit, que já tinha recusado o Pillow 12.x. As versões estão fixas no `requirements.txt` desde o PR #36. Quando o `pip-audit` apontar uma vulnerabilidade nova, o que faz falhar qualquer PR mesmo sem relação com a dependência, a regra é atualizar a dependência num PR próprio, com a suíte de testes passando; só se não houver versão corrigida, a exceção entra no workflow com `--ignore-vuln`, justificativa e data, e é registrada no Decision Log.

### Análise estática

O bandit apontou quatro tipos de ocorrência, todas avaliadas: um `try/except/pass` em `app/ui.py`, que ignora só a falha da navegação fora do contexto de várias páginas (nos testes); SQL montado com texto em três scripts, falso positivo porque os nomes de tabela e coluna são constantes do código e caminhos e valores vão como parâmetro, e nenhum desses scripts recebe entrada do visitante; uso de `subprocess` só para `git rev-parse HEAD`, com argumentos fixos e sem shell; e `random` em amostragem estatística com semente fixa, e não em criptografia. A aplicação não monta SQL com valores digitados.

### Link público

Conferido no navegador em 24/11/2026:

- HTTPS com `Strict-Transport-Security: max-age=63072000; includeSubDomains`, emitido pelo Replit;
- cookie `_streamlit_xsrf` presente, ou seja, proteção contra requisição forjada ativa;
- os caminhos `/data/analytics/dist_exata.parquet`, o mesmo caminho com `..` pelo servidor de estáticos e `/app/assets/radar-enem.jpg` devolvem a página da aplicação, nunca o arquivo;
- `checar_saude.py` com a lista de artefatos expostos vazia em 19/11 e 24/11.

### Servidor de arquivos estáticos

O servidor de estáticos do Streamlit foi ligado para servir as fontes (DL-09), com quatro condições: `app/static/` só contém as fontes e a licença; os artefatos ficam em `data/analytics/`, fora da pasta servida; caminhos com `..`, inclusive codificados, são recusados pelo Streamlit com HTTP 400; e a conferência é automática, porque o `checar_saude.py` tenta baixar os cinco artefatos por caminhos diretos e pelo servidor de estáticos e falha se algum responder com um Parquet.

### Revisão de QA do ADR-001

A revisão de QA do ADR-001, pendente desde 03/11, foi feita no pente fino. Cada ação prevista (CDF só no backend, nada versionado, nada servido, piso na exibição, limites nas pontas, dependência entre medidas e não persistência) foi conferida no código, nos testes e no link público, e a tabela está em `docs/privacidade.md`.

### Risco residual aceito

O Streamlit não permite configurar os cabeçalhos `Content-Security-Policy` e `X-Frame-Options`. A aplicação não tem login nem ação que altere dados, então o risco de uma página de terceiros embutir o Radar ENEM é baixo, e foi aceito. No módulo territorial, o risco residual de inferência no meio da distribuição de grupos pequenos também foi aceito pelo PO, com a auditoria descrita na seção 4.7.

## Monitoramento, incidentes e recuperação

### Monitoramento

- Painel da publicação no Replit: estado, logs e uso de CPU e memória, com o monitoramento da aplicação ligado na publicação.
- Monitor externo: o workflow `.github/workflows/monitor-producao.yml` roda `scripts/checar_saude.py` contra o link público a cada três horas (cron `17 */3 * * *`), de fora do Replit, e pode ser disparado à mão. O job falha com código 1 se a aplicação não responder e com código 2 se algum artefato puder ser baixado. O GitHub avisa por e-mail quem acompanha o repositório, e o histórico da aba Actions é a evidência contínua de disponibilidade. As duas primeiras execuções, disparadas à mão em 24/11/2026 depois do merge do PR #39, terminaram sem falhas: em cada uma, 5 de 5 respostas do endpoint de saúde e da página inicial e nenhum artefato baixado. Ele substitui o serviço de terceiros previsto inicialmente (UptimeRobot), sem cadastro nem segredo, e faz só requisições de leitura. O GitHub desativa workflows agendados depois de 60 dias sem atividade no repositório; se o projeto ficar parado depois da banca, o monitor deve ser reativado na aba Actions ou desativado junto com o link. Os workflows usam as versões das ações do GitHub que rodam em Node.js 24.

Os logs da aplicação não registram valores digitados (regra R6).

Quadro: Resposta a incidentes em produção
Larguras: 30,50,20
| Sintoma | Primeira ação | Responsável |
| --- | --- | --- |
| Link fora do ar (monitor avisa) | Abrir o painel da publicação, ler os logs e reiniciar a publicação | PO |
| Página com erro de artefato ausente | Rodar a auditoria no Shell, reenviar os arquivos de `data/analytics/` e republicar | PO |
| Lentidão acima de 3 s (RNF02) | Medir com `medir_desempenho.py --ambiente replit`; se persistir, avaliar VM dedicada (nova DL) | PO e QA |
| Suspeita de exposição de dados | Rodar `checar_saude.py`; se falhar, tirar o link do ar imediatamente | PO |
Fonte: `docs/av6/nuvem.md`, seção 7.

### Backup, RPO, RTO e rollback

- **O que pode ser perdido:** nada que não possa ser refeito. O código está no GitHub; os artefatos têm cópia com o PO e são reproduzíveis pelo pipeline a partir dos microdados com hash registrado.
- **RPO:** zero de código e de dados publicados, pelos motivos acima.
- **RTO:** estimado, não medido (DL-10). O tempo medido é o da republicação, cerca de 3 min do clique ao app no ar. Recriar do zero soma a esse tempo a importação do repositório, o envio dos cinco artefatos (cerca de 13 MB) e a configuração da Reserved VM, todos descritos passo a passo. A estimativa é de **30 a 60 minutos**, dominada por passos manuais, e não por processamento.
- **Rollback:** no Shell do projeto, voltar para o commit anterior (`git checkout <commit>`), rodar a auditoria e republicar. O commit em produção aparece no rodapé da aplicação.
