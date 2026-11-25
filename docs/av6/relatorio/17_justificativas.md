#C Justificativa técnica e metodologia das ações | Escolhas por área, motivos e alternativas descartadas

## Critério geral das decisões

As decisões técnicas do Radar ENEM seguiram três regras, aplicadas da mesma forma em todas as áreas do produto.

- **Medir antes de decidir.** Sempre que havia alternativas viáveis, a escolha foi feita por medição sobre os dados reais ou no ambiente real de publicação: motores de processamento, codecs de compressão, aproximações estatísticas, tamanho de amostra, consumo de memória da máquina virtual e custo do cache.
- **Adotar uma técnica só quando ela resolve um problema real.** Ferramentas mais sofisticadas (processamento distribuído, banco relacional, contêineres, modelos de aprendizado de máquina, testes de hipótese) foram avaliadas e deixadas de fora quando o problema que resolvem não existe neste produto. A ausência delas é uma decisão, e não uma lacuna.
- **Registrar a decisão antes de executar.** Cada escolha relevante tem entrada no Decision Log ou um ADR, com contexto, alternativas e evidência, o que permite revisar a decisão se o contexto mudar.

As seções a seguir apresentam, por área, a técnica ou arquitetura adotada, o motivo da escolha e por que as alternativas não foram usadas.

## Processamento de dados

O processamento tem duas fases com exigências opostas: transformar 7,51 GB de CSV, o que pode levar minutos, e responder a uma consulta de usuário em milissegundos, numa máquina de 2 GB. A arquitetura separa as duas fases: lote offline na máquina da equipe e leitura de artefatos pequenos no servidor.

Quadro: Processamento de dados – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Motor de processamento | DuckDB, no ETL e no app | Foi o mais rápido nas quatro edições (6 a 9 s por edição), lê o latin-1 do INEP sem conversão, gera Parquet cerca de 20% menor e é o único motor que respeitou 1 GB em todas as consultas, porque derrama para disco. pandas usou de 2,9 a 7,0 GiB; Polars exigiu conversão de codificação e ultrapassou 2 GB na consulta mais pesada |
| Processamento distribuído | Não usado | O Spark local levou de 4 a 5 vezes o tempo do DuckDB. O maior CSV tem 2,41 GB e a camada tratada inteira, 374 MB: cabem numa máquina, e a JVM só acrescentaria tempo e dependência. O Spark passa a fazer sentido se uma edição deixar de caber na memória de uma máquina mesmo com derramamento para disco |
| Modo de carga | Lote completo por edição, offline | A fonte é estática e publicada uma vez por ano. Streaming e carga incremental resolvem dados que chegam continuamente, o que não ocorre aqui; a carga completa com hash da fonte é mais simples de auditar e de reproduzir |
| ETL ou ELT | ETL | Transformar antes de publicar permite aplicar o contrato, o funil e as conferências fora do ar. Carregar o dado bruto num serviço para transformar depois (ELT) levaria o dado individual para a nuvem, o que a regra R1 proíbe |
| Ingestão | Download manual com SHA-256 conferido | Um coletor automático teria de ser mantido para uma fonte anual; o hash garante a identidade da fonte, que é o que importa para a reprodutibilidade |
Fonte: `docs/stack/README.md`, `docs/stack/benchmark.md` e seções 3.3 a 3.10.

**Metodologia.** O benchmark usou os dados reais das quatro edições, mediu tempo e pico de memória residente amostrado a cada 20 ms, repetiu as consultas cinco vezes e reportou a mediana. As consultas foram medidas num orçamento de 2 núcleos e 1 GB, que simula o servidor. A decisão de trocar o Polars, previsto no Plano de Trabalho, pelo DuckDB foi tomada a partir desses números e registrada.

## Armazenamento, formato e organização em camadas

Quadro: Armazenamento e formato – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Formato | Parquet colunar | As consultas leem poucas colunas de muitas linhas; o formato colunar lê só as colunas usadas e comprime por coluna. CSV exigiria ler e converter tudo a cada leitura |
| Compressão | ZSTD | Chega ao tamanho do gzip (101,4 MiB contra 102,4 MiB na edição de 2019) com a velocidade de escrita do snappy; os 11 ms a mais por leitura em relação ao snappy são irrelevantes diante da meta de 3 s |
| Organização | Três camadas: RAW, TRUSTED e ANALYTICS | Separa o dado original intocado, o dado tipado e conferido e o dado agregado que o app lê. Cada camada pode ser regerada a partir da anterior, e só a última sai da máquina da equipe |
| Particionamento | Uma partição por edição, gravada por consulta separada | Uma consulta sobre uma edição lê de 73 a 114 MB em vez de 374 MB. O `PARTITION_BY` do DuckDB dobrava o pico de memória (5,1 GB contra 2,4 GB) e foi descartado. A partição também é uma fronteira estatística: as edições não se comparam (seção 4.11) |
| Pré-agregação | CDF exata e faixas protegidas por grupo | Reduz o que o app lê de 374 MB para 12,6 MB e o percentil passa a sair por busca binária em 0,11 ms. Consultar o dado individual a cada pedido levaria de 71 ms a 1,04 s e até 497 MB de memória |
| Banco relacional ou NoSQL | Não usado | Não há escrita, transação, usuário nem relacionamento a manter: o app lê distribuições inteiras, uma vez, em memória. Um SGBD acrescentaria um serviço para operar sem resolver nenhum problema |
| Lakehouse (Delta Lake, Iceberg) | Não usado | Resolve atualização, merge e histórico de versões de tabela, que o produto não tem; a versão do dado é controlada por hash e manifesto |
| Armazenamento de objetos | Não usado | Os artefatos mudam no máximo uma vez por edição e cabem no projeto publicado; buscar de um serviço externo exigiria código de download e credencial |
Fonte: `docs/stack/benchmark.md`, relatório da AV3 e seções 3.2, 3.7, 3.9 e 6.5.

## Modelagem e integridade dos dados

A camada lida pelo app foi modelada como uma tabela fato de distribuição, com o grão definido em uma frase (seção 3.8), e não como um esquema relacional normalizado.

Quadro: Modelagem e integridade – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Grão da camada analítica | Uma linha por nota distinta, edição, área e grupo | É o menor nível que permite calcular qualquer percentil, média, desvio e quantil exatamente, sem guardar nenhum dado individual |
| Medidas prontas ou calculadas | Calculadas pelo motor a partir das linhas | Guardar médias prontas levaria ao erro de combinar médias de grupos de tamanhos diferentes; as linhas permitem recalcular tudo |
| Dimensões | No código de cada módulo | São pequenas e estáveis (5 áreas, 4 edições, 27 UFs, 6 faixas, 6 níveis); tabelas de dimensão com chaves substitutas não trariam ganho num conjunto somente leitura de 12,6 MB |
| Camada tratada (TRUSTED) | Tabela larga, sem normalização | É lida por varredura colunar e nunca atualizada linha a linha, então não sofre as anomalias de atualização que a normalização evita |
| Restrições de integridade | Verificadas por código antes de publicar | Chave do grão única, frequência positiva, faixa de nota, CDF coerente, total do Brasil igual entre artefatos e piso de 100, conferidos por `auditar_artefatos.py`. Sem SGBD, as restrições que um esquema declararia viram uma barreira de publicação |
| Fonte única do esquema | Contrato em `scripts/colunas.py` | O ETL e a documentação leem o mesmo contrato; manter listas de colunas em dois lugares abriria espaço para divergência |
Fonte: `docs/modelagem/README.md` e seções 3.4 e 3.8.

## Método estatístico

O ponto de partida do método é a natureza dos dados: cada edição entra inteira, de modo que as medidas são parâmetros populacionais calculados exatamente.

Quadro: Método estatístico – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Base de cálculo | População inteira de elegíveis | Uma amostra de 1% erraria os quantis de Matemática em até 6,0 pontos de nota, e estratificar por UF não reduziu o erro (seção 4.10). Processar a população custa cerca de dois minutos offline |
| Percentil | Exato, pela CDF empírica, com posto médio | A curva normal erraria em até 8,6 pontos percentuais, por causa da assimetria das notas da TRI (seção 4.9). As faixas interpoladas do MVP erravam até 0,0047 pp, e a equipe preferiu não chamar de exato um valor aproximado (ADR-001) |
| Empates | Posto médio (quem tirou a mesma nota conta metade) | Usar só "abaixo" ou "até" a nota deslocaria a posição em grupos com muitas notas iguais, como na Redação, em múltiplos de 20 |
| Variância e mediana | Variância populacional; mediana inferior | O divisor N corresponde a populações completas; a mediana inferior é sempre uma nota que alguém obteve e segue a regra de todos os quantis (DL-01) |
| Comparação entre grupos | Probabilidade de superioridade e diferença em pp | Mede o tamanho da diferença numa linguagem que o público entende ("sorteando uma pessoa de cada grupo") e equivale à estatística U de Mann-Whitney normalizada |
| Testes de hipótese e intervalos de confiança | Não usados | Não há erro amostral numa população completa; com milhões de participantes, qualquer teste daria p praticamente zero e não distinguiria diferença relevante de irrelevante (seção 4.6) |
| Z-Score | Exibido só como distância à média | Convertido em percentil pela normal, repetiria o erro de até 8,6 pp |
| Boxplot | Caixa protegida, bigodes em P5 e P95 | O boxplot clássico desenha mínimo, máximo e pontos isolados, que são notas de pessoas sozinhas |
| Comparação entre edições | Não feita; drift medido | As distribuições mudam entre edições (D de Kolmogorov-Smirnov até 0,149); a nota 650 em Matemática vai do percentil 85,8 em 2019 a 81,4 em 2022 |
| Moda | Não exibida | Nas áreas objetivas há mais de seis mil notas distintas por edição; a moda seria uma nota qualquer com poucas pessoas a mais que as vizinhas |
| Previsão de aprovação ou modelos preditivos | Não usados | Não há variável-alvo nem decisão a automatizar; a aprovação depende de curso, vagas, cotas e concorrência, que os dados não contêm. Prever aprovação induziria leitura errada do resultado |
Fonte: `docs/av6/estatistica.md`, `docs/av6/analises_av6.json`, ADR-001, DL-01 e capítulo 4.

**Metodologia.** As alternativas estatísticas não foram descartadas por enunciado, mas por análise sobre os dados reais: o erro da aproximação normal em todas as notas observadas de cada edição e área; 200 amostras de cada desenho amostral para medir o erro dos quantis; e KS e PSI entre todas as edições, para medir quanto as distribuições mudam. As análises estão em `scripts/analises_av6.py`, e o resultado, com os hashes das entradas, em `docs/av6/analises_av6.json`.

## Privacidade e proteção de dados

O produto mostra recortes socioeconômicos de uma base de milhões de pessoas e recebe dados pessoais do visitante. As escolhas desta área seguem a LGPD e o princípio de expor o mínimo necessário para responder à pergunta.

Quadro: Privacidade – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Tamanho mínimo de grupo | Piso de 100 participantes | Dá folga sobre o mínimo estatístico usual de 30 e impede exibir grupos em que uma pessoa pesa mais de 1% do resultado |
| Onde fica a CDF exata | Só no backend | Tem linhas com frequência 1; publicá-la, versioná-la ou servi-la como arquivo revelaria notas de pessoas isoladas (ADR-001) |
| Pontas do percentil em grupos menores que o Brasil | "Acima de X%" e "abaixo de X%", limite arredondado e conta em inteiros | Testar notas vizinhas numa UF pequena revelaria a nota de uma pessoa; a regra por contagem de pessoas acima gerava rótulos falsos com empates, e o limite sem arredondar gerava 281 inversões em 640 grupos (DL-04) |
| Diferença entre posições | Omitida se uma delas estiver em limite | Somada à posição exata do outro grupo, devolveria o valor escondido |
| Recortes oferecidos | Renda, UF de prova e escolaridade dos pais | Cor ou raça é dado sensível e ficou de fora; município e UF da escola gerariam grupos pequenos e dedução por diferença; cruzamentos livres multiplicariam células pequenas |
| Dados do visitante | Só na sessão, nunca persistidos | Gravar ou registrar notas e perfil não traria benefício ao usuário e criaria um tratamento de dado pessoal sem finalidade; as entradas não vão para URL, log nem serviços de terceiros |
| Fontes tipográficas | Servidas pelo próprio app | Buscar as fontes num serviço externo enviaria o IP de cada visitante a um terceiro (DL-09) |
| Telemetria e análises de visitantes | Desligadas | Mesma razão: nenhum dado do visitante sai da sessão |
Fonte: `docs/privacidade.md`, ADR-001, DL-04, DL-09 e seções 4.7 e 5.9.

## Aplicação e visualização

Quadro: Aplicação e visualização – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Framework web | Streamlit, com Plotly | Uma única base de código em Python, a mesma linguagem do pipeline e do motor. Uma aplicação React com FastAPI exigiria duas bases de código e duas publicações; o custo fixo de memória dos frameworks avaliados foi equivalente (73 a 100 MB ociosos) |
| Cache dos artefatos | `st.cache_resource`, com o dado congelado | Um único objeto compartilhado por todas as sessões. O `st.cache_data` copiava até 37 MB a cada clique; a troca levou a página territorial de 611 ms para 23 ms. O congelamento impede que uma sessão altere o dado de outra |
| Leitura do resultado | Visão simples e visão técnica | Um único nível de detalhe deixaria o público geral sem leitura ou o técnico sem detalhe; a visão simples usa frequência natural ("cerca de 81 em cada 100") |
| Distribuições | Histograma de faixas protegidas e curvas sobrepostas | Mostram a forma da distribuição e a posição da nota sem expor grupos pequenos |
| Medianas das 27 UFs | Gráfico de pontos | O gráfico de barras com eixo cortado exagerava diferenças entre estados; no gráfico de pontos a leitura é de posição, e o eixo ajustado não engana |
| Cores | Papel fixo por grupo, paleta segura para daltonismo, contraste testado | A cor nunca é o único código (a nota do usuário também tem forma própria); um teste automatizado falha se uma cor perder contraste em qualquer tema |
| Gráficos de pizza, velocímetros, metas e semáforos | Não usados | O produto descreve uma posição, sem meta nem ação esperada; esses formatos sugerem desempenho bom ou ruim, o que o produto não avalia |
| Responsividade | Layout do Streamlit conferido em 375 e 390 px | Parte do público acessa pelo celular; as quatro páginas foram conferidas nos dois temas |
Fonte: `docs/stack/README.md`, `docs/indicadores.md`, `docs/qa/relatorio-qa-av6.md` e capítulo 5.

## Hospedagem e arquitetura em nuvem

Quadro: Hospedagem – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Provedor | Replit, projeto privado | Aceita os artefatos fora do repositório, só no backend. Streamlit Community Cloud e Hugging Face Spaces publicam a partir do repositório, o que exigiria versionar os artefatos (proibido pela R1) ou buscá-los de outro serviço com credencial |
| Modelo de serviço | PaaS | A plataforma cuida de sistema operacional, runtime, TLS e disponibilidade. Uma VM própria (IaaS) exigiria operar tudo isso para uma aplicação sem estado que lê cinco arquivos |
| Tipo de publicação | Reserved VM sempre ligada (0,5 vCPU, 2 GB) | O Autoscale desliga a instância sem acesso, e a primeira visita pagaria a carga de 2,2 milhões de linhas. FaaS não comporta a conexão WebSocket e a sessão do Streamlit |
| Dimensionamento | Medido antes de decidir | Pico de 838 MiB (41% da memória) e consultas p95 até 416 ms; a VM dedicada de 1 vCPU e 4 GB ficou registrada como resposta, sem ter sido necessária |
| Contêiner (Docker) | Não usado | A plataforma monta o ambiente a partir do `.replit` e do `requirements.txt`; o Dockerfile da AV3 fica como alternativa de portabilidade |
| Banco de dados gerenciado | Não usado | Não há dado transacional e o produto não pode persistir a entrada do usuário (RNF04) |
| Rede privada, sub-redes e NAT | Abstraídos pela plataforma | Há um único ponto de entrada HTTPS e nenhum serviço interno a isolar |
| Atualização do código | Só pelo GitHub, por PR revisado; a cópia do Replit é igualada à `main` | Evita que correções automáticas da plataforma entrem no produto sem revisão, como ocorreu com uma correção do Centro de segurança (seção 6.7) |
| Uso do agente de IA da plataforma | Só para configurar, com prompt fechado e versionado | Mantém a regra de que nenhum código do produto é alterado fora do repositório |
Fonte: DL-06, DL-08, `docs/av6/nuvem.md` e capítulo 6.

## Qualidade, segurança e operação

Quadro: Qualidade, segurança e operação – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Dados dos testes | Microdados sintéticos gerados em tempo de execução | Os testes rodam em qualquer máquina e no CI sem nenhum dado do INEP no repositório; casos com resultado conhecido conferem o cálculo |
| Exatidão do resultado publicado | Conferência contra contagem direta no dado individual | Testes com dados sintéticos não provam que a CDF real está certa; a conferência na carga mostrou divergência de 0,0 pp |
| Integração contínua | GitHub Actions com testes, linter, auditoria de dependências, piso e bloqueio de arquivos de dados | Barra o problema antes do merge, e não depois da publicação |
| Dependências | Versões fixas e `pip-audit` | A instalação fica reproduzível e auditável; a plataforma já tinha recusado uma versão vulnerável do Pillow |
| Barreira de publicação | `auditar_artefatos.py` com saída 0 obrigatória | Garante que o que vai para a nuvem é idêntico ao que o pipeline gerou e conferiu |
| Monitoramento externo | Workflow agendado no GitHub Actions | Verifica disponibilidade e exposição de artefatos a cada 3 h, de fora da plataforma, sem cadastro nem segredo; um serviço de terceiros exigiria conta e não testaria a exposição |
| Acessibilidade | Auditoria automática WCAG 2.1 AA e avaliação heurística | O teste com usuários externos não pôde ser feito (DL-10); as duas verificações cobrem parte do risco sem depender deles |
| Recuperação | Republicação medida; recriação estimada | Recriar do zero às vésperas da entrega arriscaria o link em produção (DL-10) |
Fonte: `.github/workflows/`, `docs/qa/relatorio-qa-av6.md` e seções 4.12, 6.9 a 6.12.

## Processo e governança

Quadro: Processo e governança – escolhas e alternativas
Larguras: 20,22,58
| Decisão | Escolha | Por que a escolha e por que não as alternativas |
| --- | --- | --- |
| Forma de trabalho | Iterativa, em sprints associadas às avaliações | Cada avaliação exigia um incremento funcional; ciclos curtos permitiram reduzir escopo cedo quando um módulo atrasou |
| Integração de mudanças | Pull Request revisado por outro integrante | Garante uma segunda leitura do código e dos documentos antes do merge; nos PRs da AV6 as revisões resultaram em correções reais |
| Registro de decisões | Decision Log e ADR | Torna explícito o motivo de cada escolha e permite revisá-la depois; decisões só no chat da equipe se perderiam |
| Autoria dos módulos | Um autor por módulo, lógica separada e testada | Cada integrante responde pelo próprio módulo; um teste impede que um módulo importe a lógica de outro |
| Controle de escopo | Corte do quarto módulo antes de transferir autoria | Preservou a qualidade dos três módulos entregues em vez de dividir o esforço em quatro incompletos (DL-07) |
| Versões | Tags por avaliação e release `v1.0` | Permitem voltar exatamente ao estado entregue em cada marco |
| Quadro de tarefas | Issues para cobrança; quadro Kanban não mantido | Com três integrantes, o backlog ficou no Plano e no Decision Log; o quadro não foi atualizado e esse ponto fica como melhoria de processo |
Fonte: Plano de Trabalho, Decision Log e histórico do GitHub.

## Síntese das escolhas

Quadro: Síntese das escolhas por área
Larguras: 22,36,42
| Área | O que foi adotado | O que foi deixado de fora, e por quê |
| --- | --- | --- |
| Processamento | DuckDB, lote offline, ETL | Spark, streaming e ELT: sem gargalo, sem fluxo contínuo e sem permissão para levar o dado individual à nuvem |
| Armazenamento | Parquet ZSTD em três camadas, partição por edição, pré-agregação | SGBD, NoSQL, lakehouse e armazenamento de objetos: não há escrita, transação nem atualização |
| Modelagem | Tabela fato de distribuição com integridade verificada por código | Esquema normalizado e modelo estrela físico: sem ganho num conjunto somente leitura de 12,6 MB |
| Estatística | População inteira, percentil exato, probabilidade de superioridade | Amostra, curva normal, testes de hipótese e previsão: erros medidos ou sem sentido numa população completa |
| Privacidade | Piso, limites de exibição, CDF no backend, nada persistido | Recortes sensíveis, municípios e cruzamentos livres: risco de identificação |
| Aplicação | Streamlit, duas visões, gráficos escolhidos pela tarefa | Duas bases de código, pizza, velocímetros e metas: custo sem ganho ou leitura indevida |
| Nuvem | PaaS, Reserved VM, código só pelo GitHub | IaaS, FaaS, Autoscale, Docker e banco gerenciado: operação a mais ou partida a frio |
| Qualidade e operação | Testes sintéticos, conferência real, CI, barreira de publicação, monitor externo | Teste com usuários e RTO medido: impossíveis no prazo, registrados como limitação |
Fonte: elaborado pela equipe a partir das seções 8.2 a 8.9.

O padrão que se repete em todas as áreas é o de escolher a solução mais simples que atende ao requisito medido, e de registrar por que as soluções mais complexas não foram necessárias. Esse padrão manteve o produto pequeno o bastante para caber numa máquina de 0,5 vCPU, auditável por qualquer pessoa no repositório e reproduzível a partir da fonte pública do INEP.
