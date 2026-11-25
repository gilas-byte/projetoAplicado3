# AV6 — Hospedagem em nuvem: modelo de serviço, segurança, custo e operação

Documento de apoio ao relatório final (AV6, critério "Resultados, Conclusões e Validação
da Aplicação em Nuvem"). Descreve como o Radar ENEM está hospedado no Replit (DL-06), por
que a arquitetura é essa e não a de referência da disciplina, e quais evidências mostram
que o app está implantado.

- **Decisões:** DL-06, DL-08 e DL-09 (`docs/decisoes/README.md`).
- **Passo a passo:** `docs/deploy/replit.md`.
- **Barreira antes de publicar:** `scripts/auditar_artefatos.py`.
- **Medições:** `scripts/medir_desempenho.py` (servidor) e `scripts/checar_saude.py` (rede e
  privacidade), com resultados em `docs/deploy/medicoes/`.

## 1. Modelo de serviço e de implantação

O Replit é usado como **PaaS** (plataforma como serviço) em **nuvem pública**
(Computação em Nuvem, aulas 2 e 3). A equipe entrega o código e a configuração
(`.replit`); a plataforma fornece o sistema operacional, o runtime Python, a rede, o TLS
e a execução contínua. O tipo de publicação é **Reserved VM, máquina compartilhada
(0,5 vCPU, 2 GB)**: uma instância sempre ligada, sem escala a zero.

**Por que PaaS e não IaaS.** Uma VM própria (IaaS, como na aula 5) exigiria da equipe
patches do sistema, firewall, TLS, reinício automático e monitoramento, para um app sem
estado que lê cinco arquivos pequenos. O PaaS transfere essa operação ao provedor, que é
justamente o critério da aula 3 para escolher PaaS: aplicação web que adere ao padrão da
plataforma e quer reduzir administração.

**Por que não serverless (FaaS).** O Streamlit mantém uma conexão WebSocket e o estado da
sessão por usuário durante toda a visita. Funções serverless têm execução curta e sem
estado, e a partida a frio afetaria a primeira consulta. A aula de modernização
(PaaS e Serverless) indica FaaS para operações curtas orientadas a evento, o que não é o
caso.

**Por que Reserved VM e não Autoscale.** O Autoscale desliga a instância sem acesso, e a
primeira abertura do Recorte territorial carrega 2,2 milhões de linhas (10,4 s no teste
local de 03/11). Para a banca e para quem abrir o link do relatório, a resposta precisa
ser imediata. O custo da instância sempre ligada está na seção 6.

## 2. Responsabilidade compartilhada

| Camada | Quem cuida | Como |
| --- | --- | --- |
| Hardware, rede física, virtualização | Replit | Plataforma |
| Sistema operacional e runtime Python | Replit | Ambiente Nix do Replit, `modules = ["python-3.12"]` no `.replit` |
| TLS (HTTPS) e domínio `*.replit.app` | Replit | Automático na publicação |
| Disponibilidade da instância | Replit | Reserved VM sempre ligada |
| Código da aplicação | Equipe | GitHub (`main`), importado pelo Replit |
| Dependências | Equipe | `requirements.txt` com versões fixas |
| Dados publicados (artefatos da ANALYTICS) | Equipe | Enviados à mão ao projeto privado; conferidos por `auditar_artefatos.py` |
| Privacidade (piso, CDF só no backend, não persistência) | Equipe | R1 a R7 de `docs/privacidade.md`, ADR-001, DL-04 item 8 |
| Acesso à conta e ao projeto | Equipe (PO) | Conta pessoal do PO, projeto privado |
| Monitoramento e resposta a incidentes | Equipe, com ferramentas do Replit | Seção 7 |

A plataforma não assume a privacidade dos dados nem a correção do conteúdo publicado:
essas continuam com a equipe (aula 3; responsabilidade compartilhada).

## 3. Comparação com a arquitetura de referência da disciplina

As aulas de Computação em Nuvem usam o próprio Radar ENEM como exemplo: aplicação Python
em Docker (aulas 3 a 5), modernização para PaaS e serverless (aula 6), PostgreSQL com
volume persistente (aula 9) e rede virtual com sub-redes pública e privada (aula de redes
virtuais). O produto da equipe não usa todos esses componentes, e cada ausência tem
justificativa:

| Componente da referência | No Radar ENEM | Justificativa |
| --- | --- | --- |
| Docker | Não usado | O Replit monta o ambiente a partir do `.replit` e do `requirements.txt`. O esboço de Dockerfile em `docs/av3/EVOLUCAO-FUTURA-NUVEM.md` nunca foi construído e fica como alternativa de portabilidade, não como parte da entrega. |
| PostgreSQL | Não usado | O app não tem entidade transacional: não há cadastro, login nem gravação. O RNF04 proíbe persistir o que o usuário digita. Os dados são distribuições agregadas, somente leitura, que cabem em 13 MB de Parquet e são lidas em memória. Um banco relacional só seria justificado para dados operacionais, que o produto não tem. |
| Rede virtual com sub-redes, NAT e security groups | Abstraído pela plataforma | Há um único ponto de entrada público (HTTPS do Replit) e nenhum serviço interno: não existe banco, fila ou API separada para isolar em sub-rede privada. A tabela de fluxos está na seção 4. |
| Armazenamento de objetos para os microdados | Fora da nuvem | O RAW (7,5 GB) e a TRUSTED ficam no computador da equipe; o ETL roda offline (relatório da AV3). Só os artefatos agregados sobem, como arquivos do projeto (seção 5). |
| Função serverless de processamento | Não usada | Seção 1. O processamento pesado já é offline, em lote. |

O que o produto mantém da referência é o princípio da aula 8 e do laboratório da aula 9:
**separar o ciclo de vida dos dados do ciclo de vida da aplicação**. O código vem do
GitHub; os dados vêm do pipeline, com hash conferido, e não entram no repositório.

## 4. Fluxos de rede (origem, destino, porta)

| Origem | Destino | Protocolo e porta | Justificativa |
| --- | --- | --- | --- |
| Navegador do usuário | Proxy do Replit (`*.replit.app`) | HTTPS 443 e WebSocket seguro | Único acesso público |
| Proxy do Replit | Processo Streamlit na VM | HTTP 8501 interno (`localPort` → `externalPort` 80 no `.replit`) | Encaminhamento da plataforma; a porta 8501 não fica exposta diretamente |
| Processo Streamlit | Arquivos `data/analytics/*.parquet` | Leitura local | Nenhum acesso de rede para os dados |
| App | Serviços de terceiros | Nenhum | Sem telemetria do Streamlit (`gatherUsageStats = false`), sem fontes ou scripts externos (fontes IBM Plex em `app/static/`) |
| Monitor externo de disponibilidade (opcional) | `/_stcore/health` | HTTPS 443 | Só lê o status, não envia dados |

Exposição desnecessária conferida: `scripts/checar_saude.py` tenta baixar os cinco
artefatos por caminhos diretos e pelo servidor de arquivos estáticos (com `..`,
inclusive codificado) e falha se algum responder com um Parquet. No teste local de
16/11/2026, nenhum caminho devolveu artefato: o servidor estático recusa `..` com
HTTP 400 e os demais caminhos devolvem a página do app.

## 5. Armazenamento

| Dado | Tipo de armazenamento (aula 8) | Onde | Retenção e cópia |
| --- | --- | --- | --- |
| Código | Repositório Git | GitHub (`main`) e cópia no projeto do Replit | Histórico completo no GitHub |
| Artefatos da ANALYTICS (5 arquivos, 12,6 MB) | Arquivo no disco do projeto, incluído na publicação | Projeto privado do Replit, pasta `data/analytics/` | Cópia de referência no computador do PO; hashes em `docs/deploy/artefatos.sha256` |
| Microdados (RAW) e TRUSTED | Arquivo local | Computador da equipe | Hash dos zips em `data/raw/hashes.sha256` |
| Dados digitados pelo usuário | Nenhum | Só na memória da sessão | Não persistidos (R6) |

**Comportamento do disco na publicação.** A publicação do Replit é uma cópia congelada
do projeto: arquivos gravados pelo app durante a execução se perdem a cada nova
publicação ou reinício. Isso não afeta o Radar ENEM, que não grava nada, e os artefatos
entram na cópia porque estão no projeto antes de publicar. Qualquer troca de artefato
exige nova publicação (`docs/deploy/replit.md`).

**Alternativa não adotada.** O Object Storage do Replit (armazenamento de objetos
privado) permitiria trocar os artefatos sem republicar e manter versões. Ficou de fora
porque exige código de download na inicialização e credencial, e os artefatos mudam no
máximo uma vez por edição do ENEM.

## 6. Custo (FinOps)

Hipóteses, com preços da documentação do Replit consultada em 16/11/2026 (sujeitos a
mudança; conferir no painel de Billing antes de cada decisão):

| Item | Hipótese | Valor |
| --- | --- | --- |
| Reserved VM compartilhada (0,5 vCPU, 2 GB) | Sempre ligada | US$ 0,0208 por hora, cerca de US$ 15 por mês |
| Período até a banca | 16/11 a 01/12/2026, 15 dias | cerca de 360 h, cerca de US$ 7,50 |
| Transferência de dados | Uso acadêmico, poucas dezenas de visitas | Desprezível frente à VM; conferir no painel |
| Armazenamento | 12,6 MB de artefatos no projeto | Desprezível |
| Créditos mensais do plano Core do PO | Abatem o custo da publicação | Valor exato conferido no painel da conta |

**Comparação de cenários (aula 4, CAPEX e OPEX).** Não há CAPEX: nenhum servidor foi
comprado. O OPEX é a VM. O Autoscale custaria menos com pouco acesso, mas com partida a
frio; uma VM dedicada (1 vCPU, 4 GB) daria folga de memória por cerca de US$ 35 por mês.
A escolha da compartilhada depende da medição de memória no Replit (seção 7): o teste de
16/11 no ambiente de desenvolvimento mostrou pico de cerca de 1,2 GB com as quatro
páginas carregadas no mesmo processo, dentro dos 2 GB, mas com margem menor que a
estimativa de 600 MB da DL-06.

**Controles de custo.**
- Conferir o consumo no painel de Billing do Replit uma vez por semana até a banca.
- Agente de IA do Replit só para configurar a publicação, com prompt fechado da equipe e
  sem alterar código do produto (DL-08, item 4); conferir os créditos antes e depois.
- Depois da banca (01/12/2026), decidir entre manter o link (extensão) ou desligar a
  publicação; o registro vai para uma DL nova.

## 7. Operação: monitoramento, incidentes, backup e rollback

**Monitoramento (RNF05).**
- Painel da publicação no Replit: estado, logs e uso de CPU e memória.
- Monitoramento do app oferecido pelo Replit ao publicar (opção "Enable app monitoring",
  disponível no plano Core), quando aparecer para o tipo de publicação escolhido.
- Monitor externo de disponibilidade e de privacidade: o workflow
  `.github/workflows/monitor-producao.yml` roda `scripts/checar_saude.py` contra o link
  público a cada 3 horas, de fora do Replit (GitHub Actions), e falha se o app não
  responder ou se algum artefato puder ser baixado. O GitHub avisa por e-mail quem
  acompanha o repositório, e o histórico na aba Actions é a evidência contínua de
  disponibilidade. Substitui o serviço de terceiros (UptimeRobot) previsto inicialmente:
  usa o script da equipe e não exige cadastro nem segredo (pente fino da AV6, DL-10).
  O GitHub desativa workflows agendados depois de 60 dias sem atividade no repositório:
  com o projeto parado, o monitor precisa ser reativado na aba Actions ("Enable
  workflow"), ou desativado de vez se o link for desligado depois da banca.
- `scripts/checar_saude.py` antes de divulgar o link e antes da banca.

Os logs do app não registram valores digitados: o Streamlit roda com
`showErrorDetails = "type"` e o código não escreve as entradas em log (R6).

**Resposta a incidentes.**

| Sintoma | Primeira ação | Responsável |
| --- | --- | --- |
| Link fora do ar (monitor avisa) | Abrir o painel da publicação, ler os logs, reiniciar a publicação | PO |
| Página com erro de artefato ausente | Rodar `auditar_artefatos.py` no Shell; reenviar os arquivos de `data/analytics/` e republicar | PO |
| Lentidão acima de 3 s (RNF02) | Medir com `medir_desempenho.py --ambiente replit`; se persistir, avaliar VM dedicada (DL nova) | PO e QA |
| Suspeita de exposição de dados | `checar_saude.py`; se falhar, tirar o link do ar imediatamente | PO |

**Backup e recuperação.**
- **O que pode ser perdido:** nada que não possa ser refeito. O código está no GitHub; os
  artefatos têm cópia no computador do PO e são reproduzíveis pelo pipeline a partir dos
  microdados com hash registrado.
- **RPO (perda tolerável):** zero de código e de dados publicados, pelos motivos acima.
- **RTO (tempo para voltar):** estimado, não medido (decisão do PO em 24/11/2026, DL-10):
  medir exigiria apagar e recriar o projeto no Replit às vésperas da entrega. O tempo
  medido é o da republicação, cerca de 3 min do clique ao app no ar (24/11/2026,
  `docs/deploy/replit.md`). Recriar do zero soma a esse tempo a importação do repositório
  pelo GitHub, o envio dos cinco artefatos (cerca de 13 MB) e a configuração da Reserved
  VM, todos descritos passo a passo em `docs/deploy/replit.md`. A estimativa é de 30 a 60
  minutos, dominada por passos manuais, e não por processamento.

**Rollback.** Se uma versão nova quebrar o app: no Shell do projeto, voltar para o
commit anterior (`git checkout <commit>`), rodar a auditoria e republicar. O commit em
produção aparece no rodapé do app.

## 8. Evidências mínimas de "implantado"

Checklist de aceitação de nuvem e de produto implantado (Computação em Nuvem e
Engenharia de Dados e MLOps), aplicado ao Radar ENEM:

| Evidência | Situação | Onde |
| --- | --- | --- |
| Dependências reprodutíveis e versões registradas | Atendido | `requirements.txt` fixo; CI no GitHub Actions |
| Pipeline com logs, contagens e recuperação | Atendido (offline) | Manifestos do ETL, escrita atômica (AV3) |
| Dados publicados conferidos antes de publicar | Atendido | `auditar_artefatos.py` e `_manifesto_publicacao.json` |
| Dados pessoais e acesso mínimo documentados | Atendido | `docs/privacidade.md`; projeto privado |
| Persistência fora do disco efêmero | Não se aplica | O app não grava nada |
| Backup e restauração testados | Parcial | Cópia dos artefatos e hashes; teste de restauração na publicação beta |
| Métricas de disponibilidade, erro, latência e custo acompanhadas | Em andamento | Seção 7; medições em `docs/deploy/medicoes/` |
| Documentação de arquitetura, responsáveis, fontes e limites | Atendido | Este documento, DL-06, relatório da AV3 |
| Modelo de ML com monitoramento e rollback | Não se aplica | O produto não usa modelo de ML (`docs/av6/disciplinas.md`) |
