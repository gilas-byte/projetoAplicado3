# Possível evolução futura: hospedagem em nuvem (planejamento prévio)

> **Aviso de escopo.** Este documento registra uma **possível evolução futura**, em nível de **planejamento prévio**. **O método de hospedagem do Radar ENEM ainda não foi definido pela equipe.** O Microsoft Azure é citado **apenas como exemplo** de nuvem pública; não é decisão tomada, requisito da AV3 nem ambiente em uso. Nenhum trecho abaixo deve ser lido como algo já executado ou aprovado.

- **Situação:** planejamento prévio, sem decisão. **Nada aqui foi implantado.** Não há conta Azure usada, imagem construída em registro, custo medido nem teste de carga.
- **Contexto:** o Radar ENEM deve ser disponibilizado ao público (Plano de Ensino do Projeto Aplicado III) e a hospedagem ainda será definida. Este documento descreve, **como hipótese**, como a estrutura atual do projeto provavelmente seguiria para uma nuvem pública como o Azure, quais decisões ainda dependem de medição e o que faltaria construir.
- **Base conceitual:** Computação em Nuvem (IaaS/PaaS/serverless, Docker, armazenamento, custos, segurança) e Engenharia de Dados e MLOps (camadas, ELT em lote, idempotência, observabilidade, FinOps).

## 1. Premissas extraídas do código atual

| Premissa | Evidência |
|---|---|
| O processamento pesado é **offline** (em lote); a aplicação só consulta artefatos agregados. | `scripts/etl.py` gera TRUSTED e ANALYTICS; `app/app.py` não lê microdados. |
| O app lê dois Parquet pequenos de caminho configurável por variável de ambiente. | `RADAR_DIST_NOTAS` e `RADAR_DIST_EXATA` em `app/app.py`. |
| O app não grava nada, não usa query string e não registra notas digitadas. | `docs/privacidade.md` (R6) e teste `test_notas_nao_vao_para_a_url`. |
| A CDF exata (`dist_exata.parquet`) contém frequências finas e **não pode ser pública**. | ADR-001 e `docs/privacidade.md` (R3, seção 4). |
| O app sobe sem terminal interativo (`headless = true`) e expõe o endpoint de saúde do Streamlit. | `.streamlit/config.toml`. Teste local em 13/10/2026 com artefatos sintéticos: `GET /_stcore/health` retornou HTTP 200 (`ok`) e `GET /`, HTTP 200. |
| RAW (CSV, 7,509 GB descompactados nas quatro edições) **não precisa estar online**. | O app não depende dele; o ETL roda fora do servidor web. |

Consequência: a hospedagem do app é pequena e sem estado. O volume de dados e o custo de computação concentram-se no ETL, que não precisa rodar na mesma infraestrutura do app.

## 2. Estrutura hipotética (exemplo no Azure)

```text
Equipe (GitHub: branch engineering / main)
        │  push / pull request
        ▼
GitHub Actions  ── testes (25) + piso de privacidade ──► constrói a imagem Docker
        │                                                   │ tag = SHA do commit
        │                                                   ▼
        │                                     Azure Container Registry (ACR)
        │                                                   │ pull (identidade gerenciada, papel AcrPull)
        │                                                   ▼
Usuário ──HTTPS──► Ingress ──► Azure Container Apps (container Streamlit: app/ + scripts/)
                                      │  lê na inicialização, por identidade gerenciada
                                      ▼
                    Azure Blob Storage (contêiner PRIVADO, sem acesso público)
                      raw/        ZIPs do INEP + hashes.sha256        (camada fria, opcional)
                      trusted/    ano=AAAA/data_0.parquet             (opcional)
                      analytics/  v=<versão>/dist_notas.parquet
                                              dist_exata.parquet
                                              _manifesto_analytics.json
                      analytics/current.json  ← ponteiro de versão publicada
                                      ▲
ETL offline (notebook da equipe ou job agendado) ── grava uma pasta de versão nova e só depois atualiza current.json

Azure Monitor / Log Analytics ◄── logs, métricas e alertas do app          Key Vault (somente se surgirem segredos)
```

## 3. Mapeamento das camadas e componentes

| Elemento do projeto | Serviço Azure possível (exemplo) | Observação |
|---|---|---|
| Código (GitHub, branch `engineering`) | GitHub + GitHub Actions | Já existe `.github/workflows/qualidade.yml`; o *deploy* seria um job adicional após os testes. |
| Imagem do app | Azure Container Registry | Tag pelo SHA do commit, para rastrear qual código roda em produção. |
| App Streamlit | Azure Container Apps (ou App Service para contêineres) | Ver a seção 5; nenhuma escolha feita, depende de medição. |
| RAW (Bronze) | Blob Storage, camada fria, privado | Preserva os arquivos oficiais e os hashes; não é lido pelo app. |
| TRUSTED (Prata) | Blob Storage ou apenas local | Só necessária se o ETL passar a rodar na nuvem. |
| ANALYTICS (Ouro) | Blob Storage, **uma pasta por versão** | É o que o app consome. |
| ETL em lote | Execução local da equipe (MVP) ou Container Apps Job/VM agendados | O ETL usou 2,2 a 2,4 GB de pico no benchmark do projeto; dimensionar pelo benchmark, não por estimativa. |
| Logs e alertas | Azure Monitor / Log Analytics | Sem registrar valores digitados (R6). |
| Segredos | Key Vault | Hoje não há segredos; entra apenas se aparecerem. |

Serviços **não** recomendados para o MVP: Spark/Databricks/Synapse e bancos gerenciados (SQL, PostgreSQL, Cosmos). O volume do app é de agregados pequenos e o benchmark da equipe não mostrou ganho do Spark nesta escala. Um banco relacional só se justificaria para dados operacionais (por exemplo, cadastro de usuários), que o projeto não tem.

## 4. Como os artefatos chegam ao app

| Opção | Como funciona | Vantagens | Cuidados |
|---|---|---|---|
| **A. Baixar na inicialização (preferida para o MVP)** | Um passo de inicialização baixa a versão apontada por `current.json` do Blob privado para o disco do container e o app lê pelos caminhos de `RADAR_DIST_*`. | Sem mudança em `app/app.py`; usa identidade gerenciada com papel de leitura em Blob; arquivos pequenos cabem no disco efêmero. | Falta escrever o script de download (`scripts/baixar_artefatos.py`, hoje inexistente); o app precisa falhar de forma clara se o download falhar; cada réplica baixa sua cópia. |
| B. Azure Files montado | Compartilhamento SMB montado como volume. | Compartilhado entre réplicas e revisões. | Container Apps **não monta Blob Storage**; o armazenamento de ambiente para Azure Files é configurado com nome e chave da conta, o que cria um segredo a proteger. |
| C. DuckDB lendo `az://` direto do Blob | O DuckDB tem extensão Azure e aceita autenticação por cadeia de credenciais e identidade gerenciada. | Evita cópia local. | Exige alterar `app/app.py`, instalar/carregar a extensão no ambiente e tratar latência e falha de rede; não há necessidade comprovada para arquivos tão pequenos. |

**Publicação versionada.** O risco registrado no ADR-001 (dois Parquet substituídos em sequência, sem atomicidade conjunta) seria resolvido gravando cada execução em `analytics/v=<versão>/` e atualizando `current.json` apenas depois de os três arquivos e o manifesto estarem completos e verificados. Reverter uma versão passa a ser apontar `current.json` para a anterior.

## 5. Onde hospedar o app: comparação preliminar

| Alternativa | Pontos a favor (confirmados na documentação oficial) | Pontos de atenção |
|---|---|---|
| **Container Apps** | Ingress HTTP com WebSocket e *session affinity*; TLS 1.2/1.3 terminado no ingress, com redirecionamento de HTTP para HTTPS; regra de escala por requisições simultâneas; identidade gerenciada para ACR e Storage; Key Vault. | Escala a zero por padrão (réplica mínima 0), o que reduz custo e causa partida a frio; para manter uma instância ligada, definir réplica mínima 1. Tempo limite padrão de requisição HTTP de 240 s. Disco efêmero de 1 a 8 GiB conforme as vCPUs. |
| **App Service para contêineres (Linux)** | WebSockets sempre habilitados em apps Linux; modelo PaaS mais simples. | Em contêiner personalizado, definir `WEBSITES_PORT` (por exemplo, 8501) para a porta do Streamlit; `/home` só persiste com `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`; no plano gratuito há limite de 5 conexões WebSocket (acima disso, HTTP 429), o que limita o uso público com o Streamlit, que mantém uma conexão por sessão. |
| Máquina virtual (IaaS) com Docker | Máximo controle, equivalente ao laboratório de Computação em Nuvem. | Maior responsabilidade operacional (patches, rede, TLS, monitoramento). |
| Funções serverless | Custo ocioso mínimo. | **Pouco adequado agora:** o Streamlit mantém conexão WebSocket e estado de sessão por usuário; limites de memória/duração e partida a frio devem ser medidos antes. |

**Nenhuma alternativa foi escolhida.** Como hipótese de trabalho, Container Apps ou App Service para contêineres seriam os primeiros a avaliar, após medir CPU, memória e sessões simultâneas (próxima seção).

## 6. Dimensionamento e custo (FinOps)

1. Construir a imagem e medir o consumo com `docker stats` durante um uso representativo: carga inicial, 1, 10 e 50 sessões simultâneas, usando os artefatos reais.
2. Medir o tamanho real de `dist_notas.parquet` e `dist_exata.parquet` após o ETL com os microdados oficiais. Hoje **não há número medido**; a expectativa de arquivos pequenos (contagens agregadas por nota) precisa ser confirmada.
3. Com os valores medidos, estimar o custo mensal na calculadora de preços do Azure (CPU/memória do app, ACR, Blob, Log Analytics) e comparar as alternativas da seção 5. Este documento não informa valores em reais porque ainda não existem medições nem escolha de plano.
4. Definir orçamento e alertas de custo no Cost Management e limitar a réplica máxima, para que um pico de acessos não gere custo imprevisto.
5. Decidir entre réplica mínima 0 (mais barato, partida a frio) e 1 (resposta imediata).

## 7. Segurança e privacidade na nuvem

- Contêiner de Blob **privado**, com acesso anônimo desabilitado; leitura apenas pela identidade gerenciada do app (papel de leitura de dados de Blob). O app não recebe chave de conta.
- ACR sem usuário administrador; pull pela identidade gerenciada com o papel `AcrPull`.
- `dist_exata.parquet` nunca fica em pasta servida, não é exposto por rota e não vai para o repositório nem para a imagem (o `.gitignore` já bloqueia `*.parquet`). Não habilitar o serviço de arquivos estáticos do Streamlit.
- Logs sem valores digitados (R6). Revisar a retenção do Log Analytics.
- HTTPS obrigatório (o ingress do Container Apps redireciona HTTP para HTTPS).
- Escolher região considerando a LGPD e a disponibilidade dos serviços (por exemplo, uma região do Brasil), a confirmar com custos.
- Reavaliar o risco residual de inferência por consultas repetidas (ADR-001) antes de abrir o acesso ao público.

## 8. CI/CD e rastreabilidade

1. O workflow atual roda compile, 25 testes e o piso de privacidade.
2. Em `main` (ou `engineering`), um job de *deploy* constrói a imagem, envia ao ACR com tag igual ao SHA e atualiza o app. A autenticação do GitHub no Azure deve usar credencial federada (OIDC), evitando segredos de longa duração no repositório.
3. O ETL registra no manifesto (`_manifesto_analytics.json`) o SHA do código, os hashes e a divergência da CDF; a versão de dados em produção fica rastreável até o commit e o arquivo oficial de origem.
4. Um *quality gate* de dados antes de atualizar `current.json`: contagens conservadas, divergência da CDF dentro da tolerância e manifesto presente.

## 9. Observabilidade

- Sonda de saúde apontando para `/_stcore/health` (verificada localmente).
- Alertas: reinicializações do contêiner, taxa de erros 5xx, latência e falha ao baixar artefatos na inicialização.
- Observabilidade de dados (Aula 6): *freshness* (data da versão em `current.json`), volume (total de elegíveis por ano/área) e *schema*, todos já presentes no manifesto.

## 10. Esboço de Dockerfile (**não testado**)

O ambiente em que este documento foi escrito não dispõe de daemon Docker; o trecho abaixo é apenas um ponto de partida e precisa ser construído e validado.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY scripts/ scripts/
COPY .streamlit/ .streamlit/
ENV RADAR_DIST_NOTAS=/data/dist_notas.parquet \
    RADAR_DIST_EXATA=/data/dist_exata.parquet
EXPOSE 8501
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Itens a decidir ao validar: passo de download dos artefatos antes de iniciar o Streamlit, usuário não-root, `.dockerignore` (excluir `data/`, `tests/`, `docs/`) e `WEBSITES_PORT=8501` caso a escolha seja o App Service.

## 11. Roteiro condicional e critérios de aceite

As etapas abaixo só se aplicam **se a equipe decidir** levar a aplicação a uma nuvem; não há prazo nem responsável definidos.

| Etapa | Entrega | Critério de aceite |
|---|---|---|
| 1 | Executar o ETL com os microdados reais | Manifestos reais; tamanhos finais dos dois artefatos medidos. |
| 2 | Dockerfile e `.dockerignore` validados | Imagem constrói; `/_stcore/health` responde 200; app abre sem artefatos embutidos na imagem. |
| 3 | Script de download versionado (`current.json`) | Falha clara se o manifesto ou o hash divergirem; reversão testada. |
| 4 | Medições com `docker stats` | Tabela de CPU, memória e sessões; escolha justificada entre Container Apps e App Service. |
| 5 | Ambiente Azure de teste | Blob privado, identidade gerenciada, ACR e app no ar; acesso anônimo ao Blob recusado. |
| 6 | CI/CD de deploy | Tag da imagem = SHA; deploy só após testes e quality gate. |
| 7 | Revisão de privacidade e custo | ADR-001 reavaliado; orçamento e alertas configurados. |

## 12. Decisões ainda não tomadas e riscos

- **Se haverá hospedagem em nuvem e em qual provedor** (o Azure é só exemplo).
- Escolha do serviço, caso o provedor seja o Azure (Container Apps × App Service), e da política de réplica mínima.
- Tamanho real dos artefatos e consumo de memória por sessão (hoje não medidos).
- Disponibilidade, créditos e custos da assinatura Azure usada pela equipe/instituição.
- Quem é o responsável pela conta e pelos acessos (permissões mínimas).
- Risco de inferência por consultas repetidas sobre a CDF exata (ADR-001) em ambiente público.
- Partida a frio com escala a zero e seu impacto na experiência.

## Referências consultadas (documentação oficial, 13/10/2026)

- Microsoft Learn: Azure Container Apps — [storage mounts](https://learn.microsoft.com/azure/container-apps/storage-mounts), [scale](https://learn.microsoft.com/azure/container-apps/scale-app), [ingress](https://learn.microsoft.com/azure/container-apps/ingress-overview), [security](https://learn.microsoft.com/azure/container-apps/security).
- Microsoft Learn: [Azure App Service on Linux FAQ](https://learn.microsoft.com/azure/app-service/faq-app-service-linux).
- DuckDB: [extensão Azure](https://duckdb.org/docs/current/core_extensions/azure).
