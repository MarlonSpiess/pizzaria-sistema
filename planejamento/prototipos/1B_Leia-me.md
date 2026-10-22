# Protótipo da fatia 1B: Cadastros

Versão 0.1, 22/10/2026. Arquivo: [1B_Cadastros.html](1B_Cadastros.html). Abra no navegador do computador (duplo clique). Os dados são de exemplo e nada é gravado. Parte do [Desenho técnico do primeiro incremento](../desenho_tecnico/01_Primeiro_Incremento.md), seção 4.2.

**Critério de sucesso:** Marlon abre o protótipo, confere se as telas e as regras de preço são as que espera e diz "aprovado" ou aponta o que mudar. Com a aprovação, começa a construção da fatia 1B.

## O que o protótipo mostra

| Aba | O que mostra |
|---|---|
| Sabores | Lista com filtro por categoria, preço Grande e Broto por sabor, cadastro e edição, "tirar do cardápio" sem apagar |
| Preços por categoria | Preço padrão de Tradicionais e Especiais por tamanho; ponto de partida de um sabor novo |
| Bordas e adicionais | Preço por tamanho, cobrado à parte e somado à pizza |
| Calzones e bebidas | Produtos de preço único |
| Simulador de preço | Mostra o cálculo da pizza, incluindo Grande de dois sabores (35,00 e 50,00 resultam em 42,50), borda e adicional |
| Clientes | Busca por telefone ou nome e cadastro (nome, telefone, endereço) |
| Entregadores | Cadastro de entregadores terceiros |

## Regras que o protótipo assume (a confirmar)

- **V1:** cada sabor tem o seu preço por tamanho (decisão D1); a categoria só sugere o preço inicial de um sabor novo. (recomendo sim)
- **V2:** o preço da Grande de dois sabores é a metade do preço de cada sabor, e a metade com centavo ímpar arredonda para cima, por sabor (T4). (recomendo sim)
- **V3:** sabor, borda ou produto "tirado do cardápio" some do pedido mas continua nos pedidos antigos. (recomendo sim)
- **V4:** o preço de borda e adicional muda por tamanho (Grande e Broto). (recomendo sim; se for o mesmo nos dois tamanhos, basta preencher igual)
- **V5:** a Broto aceita só um sabor (suposição minha de 16/10/2026). (recomendo sim)
- **V6:** calzone tem preço único, sem tamanho. (recomendo sim; diga se tem mais de um tamanho)
- **V7:** o cadastro do cliente não exige CPF nem e-mail, só nome, telefone e endereço (decisão B8). (recomendo sim)
- **V8:** o cliente com mais de um endereço fica para depois do beta. (recomendo sim)

## Ainda não está no protótipo

- Ficha técnica (quantidades de ingredientes): etapa de Estoques; a planilha que Marlon vai enviar define o formato.
- Código externo de produto para o Anota Aí: aparece quando houver token.
- Carga dos sabores e preços reais: depende da lista D2.
