# Metodologia v0.1

O NegócioBench é uma avaliação exploratória de respostas estruturadas em tarefas de negócios, com revisão humana da parte aberta. Não é uma certificação de segurança, um teste de inteligência geral ou um simulador completo de operação.

## Unidade de avaliação

Uma chamada por caso e repetição, sem ferramentas, sem memória entre casos e sem retry. Todos os modelos recebem o mesmo system prompt e a mesma pergunta. O gabarito, os campos críticos e a rubrica humana não são enviados ao modelo. Apenas as descrições de campos são enviadas.

No RAG, consulta e busca são fixas e iguais para todos. Documentos têm IDs estáveis, conteúdo sintético e versões explícitas. A busca BM25 usa tokenização com remoção de acentos, um conjunto pequeno de stopwords e parâmetros k1=1,5, b=0,75. Empates usam ID. Corpus e top-K fazem parte do hash da suíte.

## Correção automática

- Um objeto JSON único é esperado; cercas completas de código JSON e um bloco inicial completo `<think>...</think>` são tolerados. Texto extra fora desse envelope falha. Objetos com chaves duplicadas ou números não finitos são recusados.
- Números têm tolerância absoluta de 0,011; booleanos não são aceitos como números.
- Booleanos e null exigem identidade de tipo/valor.
- Strings objetivas ignoram caixa e espaços nas extremidades. Não há avaliação semântica.
- Listas usam comparação de multiconjunto: ordem não importa, duplicatas importam. O campo `ordem` é comparado em sequência.
- Cada campo do gabarito vale um critério. Presença de `resposta` textual não vazia vale mais um. Campos extras não pontuam nem penalizam.
- `score_caso = 100 × critérios aprovados / total de critérios`. Qualquer campo crítico errado zera o caso.
- JSON inválido e falha de infraestrutura recebem zero. Falha de infraestrutura permanece identificada, sem ser confundida com falha de raciocínio.
- `score_categoria` é a média de todas as suas observações, incluindo repetições; `score_geral` é a média das categorias presentes. Casos recebem pesos iguais dentro de cada categoria.

O texto de `resposta` pode contradizer os campos estruturados. Isso requer revisão humana. O verificador não prova ausência de alucinação nem segurança do texto só porque um booleano está correto.

## RAG

As fontes citadas são conferidas por igualdade com o conjunto esperado, sem recompensa por citações extras. O relatório também informa recall das fontes esperadas na recuperação: fontes esperadas encontradas / total esperado. Em casos sem fonte esperada, esse recall é definido como 1.

Não há cálculo automático de fidelidade semântica de cada frase às fontes. Um modelo pode citar a fonte certa e interpretá-la mal. A revisão humana é indispensável.

A recuperação é um baseline lexical. Não há vetor, reranking, query rewriting, chunking automático ou integração com bases externas. Baterias particulares devem verificar a cobertura de fontes com `--self-check`.

Em particular, a v0.1 não se conecta a PostgreSQL/pgvector. Os resultados desta versão não avaliam busca vetorial nem o desempenho dessa infraestrutura. Consulte [RAG, PostgreSQL e pgvector](RAG-E-PGVECTOR.md) para entender a arquitetura e os limites de comparação.

## Tempo, tokens e hardware

Tempo por caso é medido com relógio monotônico, do envio da requisição à leitura/avaliação da resposta. Inclui latência, eventual carregamento do modelo, prefill e geração. A mediana usa chamadas com resposta textual recebida, inclusive JSON inválido. Erros de infraestrutura ficam fora da mediana.

Tokens vêm de `usage` do servidor. Ausência é mostrada como desconhecida, nunca inferida por contagem de caracteres. `tok/s efetivos = tokens de saída informados / tempo total das chamadas que informaram tokens`. Não é velocidade pura de geração. Não há streaming, TTFT, amostragem de VRAM, temperatura da GPU, energia ou custo elétrico.

GPU, RAM, quantização, contexto e versão do runtime são informados pelo operador. Os nomes de modelos podem apontar para pesos diferentes; o app não valida hash dos pesos. Não compare hardware pelo score de qualidade e não compare velocidade sem controlar aquecimento, quantização e configuração.

## Comparabilidade e proveniência

Cada suíte tem SHA-256 do conteúdo, documentos, system prompt, versão e identificadores do retriever/verificador. O protocolo inclui esse hash, lista de casos, repetições, temperatura, max_tokens e timeout. Os modelos não fazem parte desse hash para permitir compará-los.

O servidor/runtime e o hardware devem ser conferidos à parte. Não misture versões de suíte, protocolos, resultados incompletos ou erros de infraestrutura com resultados válidos ao concluir superioridade de modelo.

Execuções ficam em histórico cronológico, sem ranking global ou seleção automática de melhor resultado. Dados de importação, resultados e notas humanas são armazenados localmente. Uma bateria modificada recebe outro hash. Baterias antigas podem ser reimportadas para consultar seus resultados.

## Revisão humana

Utilidade, clareza e fidelidade recebem 0 a 4:

- 0: falhou no critério.
- 1: fraca; correções importantes.
- 2: parcialmente útil; precisa de ajustes.
- 3: boa; pequenos ajustes.
- 4: pronta para o cenário avaliado.

Os três critérios e o comentário ficam no relatório e não alteram o score objetivo. A interface não oculta a identidade do modelo e não fornece dupla revisão: vieses humanos continuam possíveis. Para pesquisa, faça revisão cega e documente concordância entre avaliadores fora da v0.1.

## Limites

A suíte pública é pequena, transparente e pode ser memorizada. Não usamos conjunto privado de teste, intervalos de confiança, teste estatístico de superioridade, amostra representativa de setores ou juiz LLM calibrado. Ela dá evidência exploratória sobre os casos escolhidos, não uma estimativa geral da inteligência do modelo.

Não medimos ferramentas de agentes, chamadas externas, execução de código, áudio, visão, múltiplos turnos ou concorrência. Pedidos de envio/compra/publicação são apenas decisões declaradas em dados sintéticos.

Relatos públicos precisam incluir versão da suíte, protocolo, hardware, runtime, pesos/quantização quando disponíveis, número de repetições, erros e limitações. Não apresente respostas de um servidor falso dos testes de software como desempenho de IA.
