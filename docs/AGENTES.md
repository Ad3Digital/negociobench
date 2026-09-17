# Operação por agentes de IA

O caminho principal de entrada é entregar o repositório a uma IA com acesso ao terminal. Ela pode conduzir o diagnóstico, a preparação dos testes, a execução e a leitura dos resultados. A interface visual ajuda a pessoa a inspecionar e revisar.

## Prompt pronto para a pessoa copiar

> Quero descobrir quais IAs locais funcionam no meu computador e nas tarefas do meu negócio. Use o repositório https://github.com/Ad3Digital/negociobench. Leia o AGENTS.md e conduza o processo com suas ferramentas. Primeiro confira o ambiente e os modelos locais disponíveis. Use o que já estiver instalado; me explique o que falta antes de instalar ou baixar algo. Aproveite o contexto do meu negócio que eu já forneci e pergunte somente os fatos necessários para criar os testes. Prepare uma bateria pequena, valide os gabaritos e execute um primeiro teste com um modelo local adequado, sem API paga. Depois abra o painel e me mostre respostas, tempo, erros e limitações. Não publique meus dados ou resultados.

O agente precisa de terminal para executar. Um chatbot sem essas ferramentas pode preparar o JSON e orientar a instalação, mas não operar o PC por conta própria.

## Comandos para a IA

Nos exemplos, substitua `python` por `py -3` no Windows ou `python3` no macOS/Linux quando necessário. Execute na raiz do clone.

| Comando | Efeito |
|---|---|
| `python agent.py doctor` | Diagnóstico de Python/OS, NVIDIA quando disponível e servidores locais; sem inferência |
| `python agent.py models --runtime ollama --endpoint http://127.0.0.1:11434/v1` | IDs disponíveis de modelos locais |
| `python agent.py example` | Exemplo JSON de bateria em stdout |
| `python agent.py validate` | Confere bateria AD3 e fontes RAG, sem inferência |
| `python agent.py validate --suite .local/meu-negocio.json` | Confere a bateria particular |
| `python agent.py run --runtime ollama --endpoint http://127.0.0.1:11434/v1 --model ID_REAL --profile quick` | Executa um teste rápido com o modelo escolhido |
| `python agent.py report --run-id ID_RETORNADO` | Lê o relatório completo, incluindo respostas e fontes |
| `python bench.py --suite .local/meu-negocio.json` | Abre o painel para a bateria particular |

`ID_REAL` e `ID_RETORNADO` são placeholders; copie os valores das saídas anteriores. Não os passe literalmente. `--runtime` aceita `ollama`, `lmstudio` e `llamacpp`.

Todos os comandos da CLI retornam JSON em stdout. `run` envia progresso JSONL para stderr; `--quiet` suprime esse progresso. Ajuda de sintaxe está disponível em `python agent.py --help` e `python agent.py run --help`.

## Bateria personalizada

1. Leia os fatos fornecidos e `docs/CRIAR-TESTES.md`.
2. Escreva um JSON conforme `examples/cafeteria.json`, em `.local/meu-negocio.json`.
3. Confira contas e documentos; não use a resposta do modelo testado como gabarito.
4. Rode `validate`. Corrija casos inválidos ou fontes esperadas fora da recuperação.
5. Execute os casos com os mesmos parâmetros por modelo:

```sh
python agent.py run --runtime lmstudio --endpoint http://127.0.0.1:1234/v1 --model ID_REAL --suite .local/meu-negocio.json --profile full --repeats 1 --hardware "GPU/CPU, RAM, quantização, contexto e versão do runtime conhecidos"
```

O texto de hardware acima é uma descrição a preencher, não uma detecção automática. O diagnóstico detecta somente parte do ambiente. Ausência de `nvidia-smi` não significa ausência de GPU.

Use `--profile full` para executar todos os casos da bateria própria. `quick` seleciona um caso por categoria presente; `rag` seleciona somente os casos RAG. Repita `--model ID` para comparar modelos em sequência, até oito. O padrão de `run` é uma repetição, temperatura zero, 2.048 tokens de saída e timeout de 180 segundos por caso. Esses valores são configuráveis.

## Saídas e erros

- **Código 0:** comando concluído. Em `run`, a bateria terminou sem erro de infraestrutura; consulte a nota para saber se o modelo acertou.
- **Código 2:** argumento, arquivo, contrato ou descoberta de servidor inválido. Erros de parsing do argparse aparecem em stderr; os demais incluem `ok: false` em JSON.
- **Código 3:** `run` ficou incompleto, foi cancelado ou teve erro de infraestrutura. Resultados parciais continuam salvos.

`run` retorna IDs, hashes de protocolo, resumo e `report_path`. Os arquivos completos ficam em `.local/runs/`. `report` aceita um ID, não um caminho arbitrário. `--data-dir` permite outro diretório local para execução/relatório; nesse caso, o painel padrão não encontrará esses resultados automaticamente.

O runner evita inferências simultâneas da CLI e do painel que usam o mesmo diretório de dados. O lock é liberado pelo sistema operacional quando o processo termina. Não remova arquivos para contornar uma execução em andamento.

Ctrl+C pede cancelamento; a chamada atual pode continuar até responder ou atingir o timeout. Não reinicie um teste enquanto ele ainda estiver rodando.

Abra o painel após a CLI terminar. Se já estava aberto, reinicie a instância ociosa iniciada por você para atualizar o histórico. Para casos próprios, passe a mesma `--suite`.

## Devolutiva para a pessoa

Comece pela conclusão prática e inclua:

- O que foi testado, com quais modelos e em qual configuração conhecida.
- Casos corretos, falhas importantes e exemplos de respostas.
- Tempo observado e influência possível de carregamento/contexto.
- O que depende de revisão humana e o que ainda não foi medido.
- Caminhos dos relatórios e como abrir o painel.

Evite declarar “melhor IA” com base em uma bateria pequena. Não registre uma avaliação feita por você como se uma pessoa tivesse revisado. Não publique resultados automaticamente.
