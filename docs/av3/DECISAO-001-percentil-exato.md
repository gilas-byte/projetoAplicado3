# ADR-001 — Percentil empírico exato sem divulgar frequências finas

- **Situação:** proposto; requer revisão do time e validação nos dados completos.
- **Contexto:** o plano de ensino do Projeto Aplicado III solicita percentis populacionais exatos. O MVP calcula a posição interpolando intervalos que contêm no mínimo 100 participantes, logo apresenta aproximações.
- **Decisão:** manter `dist_notas.parquet` para histogramas protegidos e adicionar `dist_exata.parquet` com (ano, área, nota, n, abaixo, total), armazenamento **exclusivamente interno** ao backend. A aplicação carrega a CDF e aplica `(abaixo + 0,5 * iguais) / total * 100`. Para nota não observada, utilizar a contagem acumulada estritamente inferior, sem interpolação.
- **Trade-off:** preserva exatidão para área/ano nacionais, aumenta o volume do artefato agregado e o risco de inferência de frequências pequenas quando mal exposto. **Não** autoriza disponibilizar CSV/Parquet internos ao usuário final.
- **Escopo:** percentil exato nacional por edição e área. Módulos de renda, escola, território e cruzamentos múltiplos ainda necessitam engenharia e auditoria de privacidade próprias.
- **Testes:** empate, nota ausente, limites, frequências inválidas e integridade de contagem. Teste real com INEP permanece pendente.
- **Alternativa descartada:** declarar percentil aproximado como exato; imprecisão metodológica contrária à rubrica.
- **Riscos residuais:** inferência por diferenças entre percentis após numerosas consultas; possível vazamento se arquivos internos forem publicados; divergência entre dois artefatos após falha durante troca de arquivos. Necessário deploy protegido e melhoria futura de publicação transacional/versionada.
- **Revisores requeridos:** responsável técnico, QA, Product Owner.
