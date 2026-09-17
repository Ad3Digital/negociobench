# Contribuir com o NegócioBench

Contribuições de casos, interface e correções são bem-vindas sob a licença MIT.

1. Abra uma issue descrevendo o cenário e o comportamento esperado, ou um PR pequeno com a alteração.
2. Use dados sintéticos e fontes que você possa compartilhar. Não copie clientes, conversas privadas, chaves ou documentos internos.
3. Revise o gabarito independentemente da saída do modelo. Uma nova pergunta precisa testar uma habilidade, não reconhecer uma frase específica.
4. Mantenha texto livre na rubrica humana. Explique campos críticos, fontes e limitações.
5. Mudanças na correção, no prompt ou no retriever precisam atualizar a versão em `cases.py` e a metodologia. Não misture scores de versões diferentes.
6. Rode `python bench.py --self-check` e `python -m unittest discover -s tests -v`. Para a interface, confira desktop e celular, teclado e ausência de recursos externos.

Para compartilhar resultados, inclua versão, protocolo, hardware, runtime, modelo/quantização, parâmetros, repetições e erros. Não envie `.local/` inteiro. Os relatórios podem conter documentos privados.

O projeto usa a biblioteca padrão do Python e HTML/CSS/JavaScript nativos. Prefira alterações simples, acessíveis e reproduzíveis.
