#C Introdução | Contextualização, problema, justificativa de impacto social e objetivos

## Contextualização

O Exame Nacional do Ensino Médio (ENEM), aplicado pelo Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP), é a principal porta de entrada para o ensino superior no Brasil. Suas notas são usadas no Sistema de Seleção Unificada (SiSU), no Programa Universidade para Todos (ProUni), no Fundo de Financiamento Estudantil (FIES) e em processos seletivos de instituições públicas e privadas. Cada participante faz quatro provas objetivas (Ciências da Natureza, Ciências Humanas, Linguagens e Códigos e Matemática), cujas notas são calculadas pela Teoria de Resposta ao Item (TRI), e uma redação corrigida em escala de 0 a 1.000, em múltiplos de 20.

Depois de cada edição, o INEP publica os Microdados do ENEM: um registro por inscrito, com as notas das quatro áreas e da redação ao lado das respostas do questionário socioeconômico (renda familiar, escolaridade do pai e da mãe, tipo de escola, cor ou raça, local de prova, entre outras). Os dados são anonimizados na origem. Desde 2020, por cautela em relação à Lei Geral de Proteção de Dados Pessoais (LGPD), o INEP adota um modelo simplificado, sem idade exata e sem código de escola, e retira da base os participantes de cadernos com poucos inscritos.

O Radar ENEM trabalha com quatro edições: 2019, 2020, 2021 e 2022. O intervalo não foi escolhido por disponibilidade, mas porque é o objeto do estudo. A edição de 2019 é a última antes da pandemia de COVID-19; 2020 e 2021 são os anos de escola fechada e ensino remoto; 2022 é a primeira retomada. O próprio exame registra o tamanho do choque. Em 2020, dos 5.523.029 inscritos na versão impressa, 2.842.332 não compareceram ao primeiro dia, uma abstenção de 51,5%, contra 23% em 2019. Em 2021, o número de inscritos caiu para 3.109.762, o menor desde 2005, enquanto a abstenção do primeiro dia voltou a 26%. Em 2022, com cerca de 3,4 milhões de inscritos, a abstenção do primeiro dia foi de 26,7% (INEP, 2021; DIÁRIO DO NORDESTE, 2022). A taxa de comparecimento voltou ao patamar anterior já em 2021, mas a base de inscritos encolheu 44% entre 2020 e 2021 e não havia se recomposto em 2022. Mudou a nota e mudou também a composição de quem fez a prova.

Nos arquivos usados pelo projeto, as quatro edições somam 17.744.217 registros e 7,51 GB de CSV descompactado, com 76 colunas cada, em codificação latin-1. A seção 3.1 caracteriza esse volume.

## Problema

O participante recebe as notas, mas não recebe contexto. Uma nota de 650 em Matemática não diz se está acima ou abaixo da mediana de quem declarou a mesma faixa de renda, quantas pessoas formam esse grupo, como a mesma nota se posiciona entre quem fez a prova no mesmo estado ou entre quem tem pais com a mesma escolaridade. O boletim individual também não permite comparar a posição de uma nota entre edições, e a comparação ingênua entre edições é enganosa, porque cada edição tem uma população diferente.

A informação que responde a essas perguntas é pública, mas na prática só chega a quem sabe manipular alguns gigabytes de CSV, conhece o dicionário de variáveis do INEP e sabe tomar as decisões que vêm antes de qualquer número: separar quem compareceu aos dois dias de quem faltou, tratar os treineiros, traduzir os códigos do questionário em categorias que mudam de rótulo entre edições, converter as faixas de renda em múltiplos do salário mínimo de cada ano (que subiu de R$ 998 em 2019 para R$ 1.212 em 2022) e definir o tamanho mínimo de um grupo abaixo do qual a comparação deixa de fazer sentido e passa a expor pessoas. Nenhuma dessas escolhas é automática, e todas alteram o resultado.

O problema tem também uma dimensão técnica, que é de arquitetura. Ler o CSV de uma edição leva dezenas de segundos e alguns gigabytes de memória, enquanto quem abre uma página web espera uma resposta em poucos segundos, e uma hospedagem de baixo custo oferece de 1 a 2 GB de memória. O produto precisa, ao mesmo tempo, ser exato, ser rápido, caber numa máquina pequena e não expor nenhum participante.

A pergunta que orienta o produto pode ser escrita de forma direta: **em que posição a nota de um participante fica entre os participantes de uma edição do ENEM, e como essa posição muda conforme o grupo de comparação?**

## Justificativa e impacto social

### Democratização de uma leitura estatística

O Radar ENEM transforma microdados públicos em informação interpretável para quem não programa. Estudantes, famílias, professores, orientadores educacionais e cursinhos populares passam a ter, em poucos cliques e sem cadastro, uma resposta que antes exigia processar dezenas de milhões de linhas. O usuário informa as próprias notas e, se quiser, a renda familiar, a UF onde fez a prova ou a escolaridade dos responsáveis; o produto devolve a posição da nota em cada grupo, o tamanho do grupo e uma explicação de como o número foi calculado. A resposta aparece em duas leituras: uma frase em frequência natural ("cerca de 76 em cada 100 participantes tiveram nota menor que a sua"), para o público geral, e uma visão técnica, com média, mediana, desvio-padrão, quartis, Z-Score e curvas de distribuição, para quem quer o detalhe.

### Leitura crítica das desigualdades educacionais

Ao mostrar a mesma nota em grupos diferentes, o produto torna visível um fato que os boletins individuais escondem: a posição de uma nota depende do grupo com que ela é comparada, e os grupos diferem sistematicamente por renda, território e escolaridade da família. Com os dados reais de 2022, uma nota de 650 em Matemática fica acima de 87,1% dos participantes da faixa de renda de mais de 1 até 2 salários mínimos, mas acima de apenas 41,3% dos participantes de escola privada com renda familiar acima de 10 salários mínimos. A mesma nota fica acima de 96,9% dos participantes cujos responsáveis nunca estudaram e de 60,8% daqueles cujo responsável tem pós-graduação. Esses números não descrevem o mérito de ninguém, e o produto não os apresenta assim: descrevem a distribuição das notas em grupos de pessoas que tiveram oportunidades diferentes. Essa leitura apoia a compreensão crítica das desigualdades educacionais sem atribuir causalidade indevida aos fatores observados, como exige o Plano de Trabalho.

### Alinhamento com a Agenda 2030

O tema dialoga com dois Objetivos de Desenvolvimento Sustentável da Agenda 2030 das Nações Unidas: o ODS 4 (educação de qualidade), em especial a meta de eliminar disparidades no acesso à educação, e o ODS 10 (redução das desigualdades). O Radar ENEM não intervém diretamente nesses objetivos, mas oferece um instrumento público, gratuito e auditável para observar a distância entre grupos no principal exame de acesso ao ensino superior do país, num período em que a pandemia aprofundou desigualdades de acesso ao ensino.

### Responsabilidade no uso dos dados

O impacto social de um produto que mostra recortes socioeconômicos depende também do que ele se recusa a fazer. O Radar ENEM não prevê aprovação, não faz ranking de pessoas, não expõe grupos com menos de 100 participantes, não permite reconstruir a nota de uma pessoa por consultas repetidas e não grava o que o usuário digita. A comparação com outro nível de escolaridade dos pais é opcional, porque pode causar desconforto em quem a lê como juízo sobre capacidade (DL-05, item 5). Essas escolhas estão detalhadas nos capítulos 4 e 5.

### Relevância técnica e acadêmica

O problema reúne, num mesmo produto, grande volume de dados, restrição de memória, compressão, consulta analítica, qualidade, governança, motor estatístico com rigor de definição e implantação em nuvem. Cada uma dessas frentes exigiu uma escolha entre alternativas, e o capítulo 8 apresenta, por área, a técnica ou arquitetura adotada, o motivo e por que as outras opções ficaram de fora.

## Objetivos

### Objetivo geral

Projetar, implementar, validar e implantar em nuvem o Radar ENEM, produto de dados web de acesso público que traduz as notas e o perfil socioeconômico informados pelo usuário em posicionamento estatístico comparativo dentro das edições de 2019 a 2022 do ENEM.

### Objetivos específicos

O quadro a seguir lista os dez objetivos específicos do Plano de Trabalho (AV1) e indica onde cada um é tratado neste relatório. A situação final de cada objetivo é avaliada na seção 7.6.

Quadro: Objetivos específicos do Plano de Trabalho e onde são tratados
Larguras: 6,64,30
| Nº | Objetivo específico (resumido) | Onde é tratado |
| --- | --- | --- |
| 1 | Caracterizar as quatro edições por profiling e formalizar contrato e dicionário de dados | Seções 3.1 e 3.4 |
| 2 | Pesquisar e comparar alternativas tecnológicas e justificar a stack | Seção 3.10 e capítulo 8 |
| 3 | Construir pipeline offline reprodutível com camadas RAW, TRUSTED e ANALYTICS | Seções 3.2 a 3.8 e 3.12 |
| 4 | Medir volumetria e desempenho do pipeline e das consultas | Seções 3.9, 6.10 e 7.2 |
| 5 | Implementar motor estatístico comum e testado, com inferência só quando pertinente | Capítulo 4 |
| 6 | Desenvolver módulos autorais de análise comparativa, um por integrante | Seções 4.8, 5.3 a 5.5 e 7.4 |
| 7 | Construir interface web responsiva e acessível, com explicações e mensagens claras | Capítulo 5 |
| 8 | Implantar versão beta e depois versão pública estável, com monitoramento e não persistência | Capítulos 6 e 7 |
| 9 | Aplicar gestão ágil e práticas de DataOps e MLOps compatíveis com o escopo | Seções 2.4, 2.5 e 3.12 |
| 10 | Produzir a documentação acadêmica com coerência entre código, metodologia e resultados | Todo o relatório e apêndices |
Fonte: elaborado pela equipe a partir do Plano de Trabalho (AV1).

## Escopo e delimitações

O Radar ENEM é um instrumento descritivo. Ele mostra a posição relativa de uma nota dentro de cada edição analisada, e nada além disso. As delimitações a seguir valem para todo o produto e são repetidas na interface, no bloco "Como a posição é calculada" de cada página:

- **Percentil não é probabilidade de aprovação.** A aprovação depende do curso, da instituição, das vagas, das cotas e da concorrência de cada processo seletivo, que o produto não modela.
- **Diferença entre grupos não é causa.** A distância entre a faixa de renda mais baixa e o grupo de escola privada de alta renda descreve as distribuições, não mede o efeito da renda sobre a nota.
- **Cada nota é comparada apenas com a própria edição.** As edições são populações diferentes, e a seção 4.11 mede o quanto elas mudam.
- **A população de comparação é a dos participantes elegíveis:** presentes nos dois dias de prova e não treineiros, com nota na área consultada (seção 3.6).
- **Quatro edições, de 2019 a 2022.** Edições anteriores ou posteriores exigem nova execução do pipeline e nova auditoria (seção 4.11).
- **Três módulos autorais.** O quarto módulo previsto no Plano (Rede de ensino de origem) saiu do escopo por decisão registrada (DL-07), depois da saída de um integrante (DL-02). Os três módulos entregues atendem ao mínimo de um módulo por integrante.

## Acesso à aplicação

A aplicação está publicada em nuvem e acessível sem cadastro no endereço abaixo. O endereço também aparece na capa, no quadro de identificação e no README do repositório.

!! Radar ENEM, aplicação web pública (Replit, Reserved VM, no ar desde 19/11/2026) || <https://radarenem-projetoaplicado3-kirasapiens.replit.app>

Para reproduzir o exemplo usado ao longo do relatório: na página inicial, escolher a edição 2022, digitar 650 no campo Matemática e clicar em "Ver minha posição"; nas páginas dos módulos, informar também a faixa de renda (alternativa D), a UF de prova (Santa Catarina) ou a escolaridade dos responsáveis (alternativa E para pai e mãe). Os resultados esperados estão na seção 7.1.

## Estrutura do relatório

O capítulo 2 apresenta o produto, os requisitos, a equipe e o processo de trabalho. O capítulo 3 descreve a metodologia de engenharia de Big Data, da fonte do INEP aos artefatos publicados. O capítulo 4 trata da metodologia estatística e do rigor analítico do backend, com as quatro análises feitas sobre os dados reais. O capítulo 5 descreve a aplicação web, com capturas de tela da versão publicada. O capítulo 6 cobre a implantação em nuvem, a garantia de qualidade, a segurança, a otimização e a operação. O capítulo 7 reúne os resultados e a validação da aplicação pelo link público. O capítulo 8 reúne a justificativa técnica e a metodologia das ações, por área, com as alternativas avaliadas e o motivo de não terem sido adotadas. O capítulo 9 apresenta as conclusões, as limitações e os trabalhos futuros. Os apêndices trazem o Decision Log resumido, a rastreabilidade no GitHub, a atuação de cada integrante, a declaração de uso de inteligência artificial e o roteiro de reprodução.
