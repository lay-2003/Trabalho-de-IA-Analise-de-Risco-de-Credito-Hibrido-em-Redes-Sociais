# Análise Crítica e XAI — Projeto SRL de Risco de Crédito
---

## 1. Por que a Lógica Relacional Importa para o Risco de Crédito?

Sistemas tradicionais de credit scoring (ex.: FICO, Serasa) avaliam o indivíduo de forma **isolada**: renda, histórico de pagamentos, dívidas existentes. Esse paradigma ignora um fator amplamente documentado em sociologia econômica — o **efeito de contágio financeiro**: a inadimplência tende a se propagar por redes sociais e de negócios.

O Prolog permite modelar esse fenômeno de forma estruturada e **verificável**: a regra `risco_conexao/3` computa recursivamente o grau de separação entre qualquer cliente e um nó inadimplente. Isso é algo que uma tabela plana de atributos simplesmente não consegue representar.

---

## 2. Arquitetura Híbrida: Forças e Limitações

### Forças

| Componente | Contribuição |
|---|---|
| **Prolog (lógica)** | Representa grafos, recursão e relações n-árias com semântica clara |
| **Regressão Logística** | Calibra numericamente o peso de cada feature com base nos dados |
| **pyswip (ponte)** | Permite consultas dinâmicas ao motor Prolog dentro do fluxo Python |

### Limitações

- **Mundo fechado (CWA):** o Prolog assume que o que não está na base é falso. Conexões não registradas são invisíveis ao modelo.
- **Viés de representação:** se grupos socioeconômicos específicos aparecem mais como inadimplentes na base, a propagação relacional pode amplificar discriminação indireta.
- **Escala:** a recursão Prolog é custosa para grafos com milhões de nós. Para produção, algoritmos de grafos em Neo4j ou NetworkX seriam mais adequados.

---

## 3. XAI — IA Explicável e Auditável

### 3.1 Interpretabilidade dos Coeficientes

A Regressão Logística é, por natureza, um modelo **caixa branca**: cada coeficiente tem interpretação direta. Exemplo hipotético de saída do pipeline:

```
Feature                    Coeficiente
-------------------------  -----------
grau_risco_rede            +0.8312   ← maior proximidade a inadimplente → mais risco
vizinhos_inadimplentes     +0.6540   ← mais vizinhos inadimplentes → mais risco
score_classico             −0.7891   ← maior score → menos risco
renda_mensal               −0.3210   ← maior renda → menos risco
```

Isso permite que um analista de crédito **justifique** uma negativa: *"Seu pedido foi recusado porque você possui conexões diretas com três clientes inadimplentes, o que aumenta sua probabilidade de inadimplência para 82%."*

### 3.2 Regras ProbLog como Auditoria

A saída do pipeline no formato ProbLog fornece uma trilha de auditoria legível por humanos:

```prolog
0.82 :: risco(joao) :- conectado_grau(joao, inadimplente, 2),
                       vizinhos_inadimplentes(joao, 1),
                       perfil_simbolico(joao, medio_risco).
```

Cada regra gerada é **falsificável**: um auditor pode verificar no arquivo `rede_social.pl` se a conexão relacional de fato existe, e no CSV se os atributos individuais foram corretamente lidos.

### 3.3 Justiça Algorítmica (Fairness)

O modelo deve ser auditado para **disparate impact**: se `grau_risco_rede` estiver correlacionado com variáveis protegidas (raça, gênero, CEP), a propagação relacional pode reproduzir discriminação sistêmica mesmo sem usar explicitamente esses atributos. Recomenda-se:

1. Calcular métricas de equidade (ex.: `fairlearn` no Python).
2. Verificar se a taxa de falsos positivos é uniforme entre grupos demográficos.
3. Aplicar restrições de equidade durante o treinamento se necessário.

---

## 4. Contribuição do SRL para uma IA Responsável

O paradigma SRL oferece três propriedades desejáveis para sistemas de crédito:

1. **Explicabilidade:** a lógica de primeiro grau expressa *por que* uma conclusão foi atingida, não apenas *qual* é o resultado.
2. **Auditabilidade:** a base Prolog é um documento formal, legível e versionável — diferente de pesos de redes neurais.
3. **Modularidade:** regras lógicas e pesos estatísticos evoluem independentemente. Uma nova regulação pode mudar uma regra Prolog sem retreinar o modelo inteiro.
