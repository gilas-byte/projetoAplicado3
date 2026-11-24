#C Conclusões | Síntese, contribuições, limitações e trabalhos futuros

## Síntese

O Radar ENEM partiu de um problema concreto: o participante do ENEM recebe as notas, mas não a posição delas entre quem tem a mesma renda, fez a prova no mesmo estado ou tem pais com a mesma escolaridade, e a informação que responde a essa pergunta, embora pública, está em 7,51 GB de microdados que só quem programa consegue usar. O objetivo geral do Plano de Trabalho era projetar, implementar, validar e implantar em nuvem um produto de dados que fizesse essa tradução. Esse objetivo foi atingido: a aplicação está publicada desde 19/11/2026 no endereço <https://radarenem-projetoaplicado3-kirasapiens.replit.app>, responde em menos de meio segundo no percentil 95, mostra a posição exata de qualquer nota nas quatro edições de 2019 a 2022 e em três recortes autorais, e foi validada pelo próprio link público.

Do ponto de vista de engenharia de Big Data, a solução mostrou que o volume do problema não exigia processamento distribuído, mas exigia arquitetura. A separação entre lote offline e consulta online, com um pipeline em DuckDB escolhido por benchmark, reduziu 7,51 GB de CSV a 374,3 MB de Parquet e, na camada lida pela aplicação, a 12,6 MB de distribuições agregadas, sem perder nenhum registro no caminho e com cada passo ligado ao anterior por hash, manifesto e identificador de execução.

Do ponto de vista estatístico, o produto trata os dados pelo que eles são: populações completas, e não amostras. O percentil é calculado exatamente pela CDF empírica, conferido contra a contagem direta com divergência de 0,0 ponto percentual; as comparações entre grupos usam a probabilidade de superioridade como tamanho de efeito; e as alternativas não adotadas foram medidas com os dados reais. A curva normal erraria o percentil em até 8,6 pontos percentuais, uma amostra de 1% erraria os quantis em até 6,0 pontos de nota, e as edições mudam o bastante entre si (D de até 0,149) para que comparar uma nota com outra edição dê a posição errada. Cada uma dessas análises justificou com números uma decisão de projeto.

Do ponto de vista de produto e de nuvem, a aplicação foi publicada em modelo PaaS, com dados fora do repositório e fora do alcance público, sem persistir nada do que o usuário digita, com acessibilidade auditada e monitoramento externo. Os resultados analíticos confirmam a premissa social do projeto: a mesma nota 650 em Matemática, em 2022, fica acima de 41,3% dos participantes de escola privada de alta renda e de 96,9% dos participantes cujos responsáveis nunca estudaram, com 81,4% na referência nacional. O produto mostra essa diferença sem transformá-la em juízo sobre pessoas e sem atribuir causa.

## Contribuições

- **Um produto público e gratuito** que torna acessível, sem cadastro e em segundos, uma leitura estatística que antes exigia processar dezenas de milhões de linhas, com duas camadas de leitura (simples e técnica) para públicos diferentes.
- **Um pipeline reprodutível e auditável** sobre os Microdados do ENEM de quatro edições, com contrato de dados gerado de uma fonte única, funil de elegibilidade sem perdas silenciosas, barreira de qualidade antes da publicação e testes que reproduzem tudo com dados sintéticos.
- **Um tratamento de privacidade estatística** que vai além do piso de tamanho de grupo: limites de exibição do percentil contra inferência por consultas repetidas, dependência entre medidas e caixa protegida no boxplot, todos auditados sobre os dados reais.
- **Evidência empírica para escolhas metodológicas** que normalmente são tomadas por convenção: o custo da aproximação normal, o erro da amostragem e a magnitude do drift entre edições, todos medidos e versionados.
- **Rastreabilidade completa** de cada número exibido até a fonte do INEP e de cada mudança no código até um Pull Request revisado.

## Limitações

- **Teste com usuários reais não realizado.** A auditoria de acessibilidade e a avaliação heurística não medem se um estudante entende o resultado sozinho. É a principal lacuna de validação do produto (DL-10).
- **Tempo de recuperação estimado, e não medido.** O RTO de 30 a 60 minutos é uma estimativa a partir de passos documentados e do tempo medido de republicação (DL-10).
- **Três módulos, e não quatro.** O módulo Rede de ensino de origem saiu do escopo depois da saída de um integrante (DL-02 e DL-07).
- **Dependência de uma conta pessoal** no Replit, com custo pago pelos créditos do plano do PO, e de uma plataforma que não permite configurar cabeçalhos como `Content-Security-Policy`.
- **Limites da própria fonte.** A base pública exclui participantes de cadernos com poucos inscritos e não traz idade exata nem código de escola; a UF usada é a do local de prova, e não a de residência; a renda está em salários mínimos, sem deflator; e a escolaridade dos pais usa o maior nível informado, com a limitação de quem responde "Não sei".
- **Risco residual de inferência** no meio da distribuição de grupos pequenos do módulo territorial, reduzido pelos limites de exibição e aceito pelo PO com registro.
- **Leitura estritamente descritiva.** O produto não explica por que os grupos diferem, não isola o efeito da pandemia e não prevê aprovação, por desenho.

## Trabalhos futuros

- Aplicar o protocolo de teste de usabilidade (`docs/qa/teste-usabilidade.md`) com três a cinco pessoas do público-alvo, medindo acerto na leitura do resultado e tempo até a resposta.
- Medir o RTO recriando a publicação a partir do zero num projeto separado, sem afetar o link em produção.
- Incorporar a edição de 2023 e as seguintes, usando a análise de drift como barreira antes da publicação.
- Retomar o módulo Rede de ensino de origem, com regras próprias e auditoria de privacidade.
- Estudar o recorte municipal com supressão complementar, para que municípios pequenos não possam ser deduzidos pela diferença.
- Publicar os artefatos em pasta versionada, com troca atômica de todos os arquivos, e avaliar o armazenamento de objetos se a atualização ficar mais frequente.
- Avaliar a migração da conta pessoal para uma conta institucional, e a possibilidade de cabeçalhos de segurança configuráveis numa hospedagem alternativa, mantendo o projeto privado e os dados fora do repositório.

## Considerações finais

O Radar ENEM foi construído como um produto de dados, e não como uma análise pontual: tem usuário, contrato, testes, operação e registro de decisões. As escolhas que mais pesaram no resultado foram as de não fazer: não usar processamento distribuído sem gargalo, não amostrar quando a população inteira estava disponível, não testar hipóteses sobre populações completas, não guardar o que o usuário digita e não mostrar o que poderia identificar alguém. Cada uma delas foi tomada com medida e registrada, o que permite à banca e a qualquer pessoa conferir, no repositório e no link público, que os números apresentados neste relatório são os mesmos que a aplicação entrega.
