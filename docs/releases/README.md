# Releases do Radar ENEM

Cada entrega avaliada recebe uma tag no GitHub apontando para o commit da `main` que
foi entregue, com estas notas. As tags das AVs anteriores à AV4 não foram criadas na
época (pendência registrada no relatório da AV3, seção 6.6); as da AV4 são
`av4-equidade-samuel`, `av4-territorial-vinicius` e `av4-capital-gilas`, uma por
capítulo autoral.

## v1.0-beta (AV6, publicação beta no Replit)

- **Tag:** `v1.0-beta`, criada na `main` depois do merge do PR das atualizações da AV6
  (deploy, estatística, engenharia e front, num único PR).
- **Link público:** registrado em `docs/deploy/replit.md` e na DL-08.
- **Artefatos publicados:** os cinco da execução de referência, com os hashes de
  `docs/deploy/artefatos.sha256`, conferidos por `scripts/auditar_artefatos.py`.

**Novidades em relação à AV4**
- Publicação no Replit como hospedagem definitiva (DL-08), com auditoria dos artefatos
  antes de publicar e checagem de saúde e de exposição depois.
- Quartis e caixa protegida (boxplot com bigodes em P5/P95) na página inicial.
- Cores com contraste acessível nos dois temas, gráfico de medianas das UFs em pontos e
  rodapé com fonte e versão dos dados.
- Análises com dados reais para o relatório: drift entre edições, Z-Score contra a
  normal e amostragem (`docs/av6/estatistica.md`).
- Manifesto da TRUSTED com `run_id`, commit e duração.

**Riscos conhecidos**
- Memória: pico de cerca de 1,2 GB com as quatro páginas no mesmo processo, medido no
  ambiente de desenvolvimento; a VM compartilhada tem 2 GB. Na beta, a publicação usou no
  pico cerca de 838 MiB (41%).
- Revisão de QA do ADR-001 pendente (concluída em 24/11/2026, DL-10).
- Teste de usabilidade com o público-alvo em andamento (`docs/qa/teste-usabilidade.md`).

**Como voltar** (rollback): republicar o commit da tag anterior, conforme
`docs/deploy/replit.md`.

## v1.0 (AV6, entrega final)

- **Tag:** `v1.0`, a criar na `main` depois do merge do PR do pente fino (DL-10) e da
  republicação no Replit.
- **Link público:** o mesmo da beta, registrado no README.
- **Artefatos publicados:** os mesmos cinco da beta, conferidos por
  `scripts/auditar_artefatos.py` antes de cada publicação.

**Novidades em relação à beta**
- Identidade visual (PR #38): logotipos do Radar ENEM e da KiraSapiens Neurotech e bordas
  e arcos em azul neon nos dois temas.
- Dependências indiretas fixadas para a verificação de segurança do Replit (PR #36).
- Artefatos em cache sem cópia: a página territorial executa em 23 ms, e não mais 611 ms
  (1 CPU).
- Legenda dos percentis com a mesma definição em todas as páginas.
- CI com linter (ruff) e auditoria de vulnerabilidades (pip-audit).
- Revisão de QA do ADR-001 concluída.

**Riscos conhecidos**
- Teste de usabilidade com o público-alvo não feito (`docs/qa/relatorio-qa-av6.md`, seção 6).
- RTO não medido; a republicação leva cerca de 3 min.
- O Streamlit não permite configurar CSP nem X-Frame-Options.

**Como voltar** (rollback): republicar o commit da tag `v1.0-beta`, conforme
`docs/deploy/replit.md`.
