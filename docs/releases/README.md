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
  ambiente de desenvolvimento; a VM compartilhada tem 2 GB. Medição no Replit na beta.
- Revisão de QA do ADR-001 pendente.
- Teste de usabilidade com o público-alvo em andamento (`docs/qa/teste-usabilidade.md`).

**Como voltar** (rollback): republicar o commit da tag anterior, conforme
`docs/deploy/replit.md`.

## v1.0 (AV6, entrega final)

A criar depois do QA e das correções da beta, antes do envio do relatório final
(19/11/2026). Mesmo formato: o que mudou desde a beta, artefatos, riscos e rollback.
