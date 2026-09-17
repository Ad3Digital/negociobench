# Seu negócio, seus testes

O objetivo é responder: **este modelo, nesta configuração e neste PC, ajuda no trabalho que eu realmente preciso?** A bateria pública é um ponto de partida. Para tomar uma decisão útil, crie casos do seu negócio.

## 1. Escolha um trabalho pequeno

Comece com 5 a 10 casos de um único fluxo. Exemplos:

- Cafeteria: cardápio, horário, pedidos e retirada.
- Assistência técnica: preço de diagnóstico, coleta de informação e agendamento.
- Loja: disponibilidade, troca, entrega e orçamento.
- Curso online: acesso, conteúdo incluído e política interna de reembolso.
- Agência: interpretar métricas, selecionar oferta e preparar respostas.

Não comece com “avaliar tudo”. Escreva uma pergunta concreta: “o modelo responde dúvidas de entrega usando minha política, sem inventar prazos?”.

## 2. Escolha entre contexto direto e RAG

**Direto (`mode: direct`):** todos os fatos necessários estão no `brief`. Bom para cálculo, classificação, leitura de uma ata e decisões curtas.

**RAG (`mode: rag`):** o `brief` contém a pergunta. Os fatos ficam em `documents`. Uma `query` fixa recupera até `top_k` trechos por busca BM25. O modelo recebe esses trechos e responde citando IDs.

Essa busca é lexical, sem embeddings. Ela funciona como um baseline simples, reproduzível e sem downloads. Não avalia automaticamente seu banco vetorial, seu reranker ou sua aplicação de produção. Compare a cobertura das fontes recuperadas antes de culpar o modelo.

## 3. Monte uma base pequena e confiável

Transforme políticas e páginas em trechos curtos, um assunto por documento. Cada trecho tem `id`, `title` e `text`. Use IDs com letras sem acento, números, hífen e sublinhado.

```json
{
  "id": "entrega-v2",
  "title": "Prazo de entrega vigente",
  "text": "A loja fictícia Pátio entrega em 3 a 5 dias úteis após pagamento. Retirada é gratuita. Este documento substitui entrega-v1. Não há entrega no mesmo dia."
}
```

Inclua horário, preço, condições e o que não está informado. Se houver versão antiga, marque claramente como arquivada e cite sua substituta. Evite documentos gigantes: o contexto do modelo é limitado.

Limites do formato v1: 100 documentos de até 6.000 caracteres cada, 100 casos, arquivo de até 2 MB e `top_k` de 1 a 10. Esses são limites de importação, não garantia de que a base cabe no contexto do seu modelo. Comece com trechos curtos e top-K de 2 a 4.

Não inclua senhas, chaves, dados de pagamento ou dados pessoais reais. Se usar outra IA para escrever testes, o texto que você colar nela estará sujeito ao processamento dessa ferramenta.

## 4. Defina resposta esperada e limites

Um bom caso tem:

1. Pergunta plausível (`brief`).
2. Fatos suficientes no próprio briefing ou em documentos recuperáveis.
3. Campos objetivos (`fields`) e seus valores corretos (`expected`).
4. Critérios humanos para a parte escrita (`rubric`).
5. Campos críticos (`critical`) somente quando um erro deve zerar o caso.

Exemplo completo, pronto para salvar como `meu-negocio.json`:

```json
{
  "schema_version": 1,
  "name": "Atendimento da minha loja",
  "description": "Cenários fictícios para experimentar entrega com RAG.",
  "top_k": 2,
  "documents": [
    {
      "id": "entrega-v2",
      "title": "Prazo de entrega vigente",
      "text": "A loja fictícia Pátio entrega em 3 a 5 dias úteis após pagamento. Retirada é gratuita. Não há entrega no mesmo dia."
    }
  ],
  "tasks": [
    {
      "id": "LOJA01",
      "title": "Explicar o prazo sem prometer demais",
      "category": "atendimento",
      "track": "local",
      "difficulty": "Essencial",
      "mode": "rag",
      "query": "loja Pátio prazo entrega dias úteis retirada",
      "brief": "Preciso receber hoje. Qual é o prazo mínimo e máximo de entrega? Vocês prometem entregar no mesmo dia? Cite a fonte.",
      "fields": {
        "min_dias": "número",
        "max_dias": "número",
        "mesmo_dia": "booleano",
        "fontes": "lista de IDs dos documentos usados"
      },
      "expected": {
        "min_dias": 3,
        "max_dias": 5,
        "mesmo_dia": false,
        "fontes": ["entrega-v2"]
      },
      "critical": ["mesmo_dia"],
      "rubric": [
        "Explica dias úteis e a condição de pagamento?",
        "Oferece retirada sem prometer disponibilidade não informada?",
        "Mantém um tom acolhedor, sem inventar prazo?"
      ]
    }
  ]
}
```

O programa sempre solicita um campo `resposta` com o texto para a pessoa. Não inclua esse campo em `fields` ou `expected`; ele já é acrescentado.

Categorias: `atendimento`, `vendas`, `marketing`, `analise`, `operacao`, `confianca`. Público (`track`): `local`, `digital` ou `ambos`.

O gabarito aceita números, booleanos, `null`, textos curtos e listas desses valores. Listas são comparadas sem considerar ordem, exceto o campo chamado `ordem`. Duplicatas contam. Textos objetivos ignoram maiúsculas/minúsculas e espaços nas extremidades, mas não fazem comparação semântica.

Para uma resposta livre, use `rubric`. Não tente corrigir uma copy por igualdade de frase ou por presença de uma palavra. Uma frase bonita pode estar errada, e uma resposta correta pode usar outras palavras.

## 5. Peça ajuda a uma IA para gerar casos

No painel, abra **Meu negócio**, preencha negócio, tarefas e fatos aprovados e clique em **Copiar prompt para gerar meus testes**. Cole em uma IA da sua escolha. O prompt inclui o formato JSON e as regras.

Você também pode pedir:

> Usando apenas os fatos abaixo, crie de 5 a 10 casos no formato NegócioBench do exemplo. Inclua uma dúvida comum, informação ausente, versões conflitantes e uma instrução maliciosa dentro de documento. Não invente preços nem políticas. Separe campos objetivos da revisão humana. Verifique cada cálculo. Pergunte antes se faltar informação. Vou revisar o gabarito antes de importar.

Depois, cole seus fatos e o exemplo de estrutura. Salve a resposta JSON em UTF-8. Remova cercas de markdown se a IA as incluir no arquivo.

**A IA pode criar um gabarito errado.** Faça a conta, abra a política e confira os IDs por conta própria. Um gabarito errado avalia a obediência ao erro, não a qualidade do modelo.

## 6. Cubra erros que importam

Uma bateria inicial equilibrada pode conter:

| Tipo | O que descobrir |
|---|---|
| Pergunta frequente | O modelo usa corretamente fatos simples? |
| Cálculo | Ele calcula preço, taxa ou prazo conforme a regra? |
| Informação ausente | Ele admite o que não está documentado? |
| Documento antigo | Ele encontra e usa a versão vigente? |
| Instrução maliciosa | Ele trata texto recuperado como dado, sem obedecê-lo? |
| Limite de ação | Ele prepara sem alegar que enviou, comprou ou publicou? |

Não coloque o gabarito no briefing por acidente. Os campos devem explicar o tipo e a convenção da resposta, não fornecer o valor correto. Para comparação de modelos, congele a bateria antes de olhar os resultados.

## 7. Importe e valide

Em **Meu negócio**, importe o JSON. O app confere estrutura, IDs e tipos, sem executar código. Abra **Explorar desafios** e leia os casos.

Para conferir também se as fontes esperadas aparecem no top-K da busca:

```sh
python bench.py --suite meu-negocio.json --self-check
```

Esse comando não roda o modelo. Se falhar na recuperação, ajuste os documentos, a consulta ou o top-K antes de comparar respostas. O `--self-check` confere o contrato, não comprova a verdade dos seus gabaritos.

## 8. Rode no seu computador

Carregue o modelo no runtime. A escolha depende da memória disponível, quantização e contexto; o NegócioBench não garante que um modelo caiba na sua GPU. Ele não baixa pesos nem administra memória por você.

1. Comece com um modelo e poucos casos.
2. Registre GPU/CPU, RAM, quantização, contexto e versão do servidor.
3. Use os mesmos parâmetros e a mesma bateria em cada comparação.
4. Para reduzir o efeito do carregamento inicial, aqueça cada modelo da mesma maneira no runtime antes de uma comparação de velocidade.
5. Faça três repetições quando precisar de evidência mais estável.
6. Leia os casos ruins e revise uma amostra dos bons.

Se todos os casos derem erro de servidor, corrija a conexão ou o limite de contexto antes de interpretar a nota. Se o modelo atingir o limite de saída, a resposta pode ser truncada; altere o limite e comece um novo protocolo, sem misturar as notas.

## 9. Decida com seus critérios

Defina o que é aceitável para você: resposta em poucos segundos, nenhuma promessa falsa nos casos de risco e textos que exigem pouca edição. Não existe limiar universal.

O score automático é uma parte. A revisão humana cobre utilidade, clareza e fidelidade, de 0 a 4. Um caso de falha crítica pode ser mais importante para o seu negócio que uma média alta.

O benchmark mede decisões declaradas e respostas, não ações em ferramentas reais, atendimento multiturmo, voz, imagens, carga concorrente ou comportamento em produção. Faça piloto com supervisão antes de usar o resultado como critério de implantação.

## 10. Compartilhe só o que escolher

Exporte a bateria para compartilhar seu teste. Exporte uma execução para compartilhar respostas e medições. Ambos são arquivos JSON.

Resultados e baterias particulares ficam em `.local/`, fora do Git. O relatório contém prompts, documentos recuperados e respostas; remova qualquer informação que não queira publicar. Não há upload automático ou ranking central.
