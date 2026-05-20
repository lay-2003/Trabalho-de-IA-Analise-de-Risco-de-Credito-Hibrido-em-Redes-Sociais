"""
===========================================================================
 pipeline_srl.py — Pipeline SRL Híbrido: Prolog + Python/Scikit-Learn
 Projeto: Análise de Risco de Crédito Híbrido em Redes Sociais
 Disciplina: ICC260 — IA: Da Lógica aos Números (SRL & Python)
 Prof. Edjard Mota
===========================================================================

Arquitetura:
  1. Base Relacional (rede_social.pl)  → fatos e regras Prolog
  2. Ponte pyswip                       → extrai features lógicas para Pandas
  3. Regressão Logística (Scikit-Learn) → aprende pesos probabilísticos
  4. Saída ProbLog-style               → regras explicáveis com probabilidade

Dependências:
  pip install pyswip pandas scikit-learn tabulate
  (SWI-Prolog deve estar instalado no sistema: https://www.swi-prolog.org)
===========================================================================
"""

import sys
import warnings
import os
import pandas as pd
import numpy as np
from tabulate import tabulate

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
#  CONFIGURAÇÃO — ajuste o caminho do .pl se necessário
# ---------------------------------------------------------------------------

PROLOG_FILE   = "rede_social.pl"
CSV_FILE      = "dados_financeiros.csv"
INADIMPLENTE_ALVO = "daniel"   # nó de risco canônico para consultas de grau

# ---------------------------------------------------------------------------
#  SEÇÃO 1 — Carregamento do Motor Prolog via pyswip
# ---------------------------------------------------------------------------

def inicializar_prolog():
    """
    Inicializa o motor SWI-Prolog e carrega a base de fatos.
    Retorna o objeto Prolog pronto para consultas.
    """
    try:
        from pyswip import Prolog
    except ImportError:
        print("[ERRO] Biblioteca 'pyswip' não encontrada.")
        print("       Instale com: pip install pyswip")
        sys.exit(1)

    if not os.path.exists(PROLOG_FILE):
        print(f"[ERRO] Arquivo '{PROLOG_FILE}' não encontrado no diretório atual.")
        sys.exit(1)

    prolog = Prolog()
    prolog.consult(PROLOG_FILE)
    print(f"[OK] Base Prolog '{PROLOG_FILE}' carregada com sucesso.")
    return prolog


# ---------------------------------------------------------------------------
#  SEÇÃO 2 — Funções de Extração de Features Lógicas (Ponte Prolog → Pandas)
# ---------------------------------------------------------------------------

def obter_grau_risco(prolog, nome: str) -> int:
    """
    Consulta a regra grau_minimo_risco/2 do Prolog.
    Retorna o menor grau de separação entre 'nome' e qualquer inadimplente.
    Retorna 999 caso não haja conexão identificada.
    """
    query_str = f"grau_minimo_risco({nome}, Grau)"
    resultados = list(prolog.query(query_str))
    if resultados:
        return int(resultados[0]["Grau"])
    return 999


def obter_num_vizinhos_inadimplentes(prolog, nome: str) -> int:
    """
    Consulta a regra num_vizinhos_inadimplentes/2 do Prolog.
    Retorna a contagem de inadimplentes diretamente conectados a 'nome'.
    """
    query_str = f"num_vizinhos_inadimplentes({nome}, N)"
    resultados = list(prolog.query(query_str))
    if resultados:
        return int(resultados[0]["N"])
    return 0


def obter_perfil_qualitativo(prolog, nome: str) -> str:
    """
    Consulta a regra perfil_risco/2 do Prolog.
    Retorna o nível simbólico: alto_risco, medio_risco ou baixo_risco.
    """
    query_str = f"perfil_risco({nome}, Nivel)"
    resultados = list(prolog.query(query_str))
    if resultados:
        return str(resultados[0]["Nivel"])
    return "indefinido"


def extrair_features_relacionais(prolog, df: pd.DataFrame) -> pd.DataFrame:
    """
    Itera sobre o DataFrame e enriquece com features lógicas extraídas do Prolog.
    Adiciona colunas: grau_risco_rede, vizinhos_inadimplentes, perfil_qualitativo.
    """
    print("\n[*] Extraindo features relacionais via pyswip...")

    df["grau_risco_rede"]          = df["cliente_id"].apply(
        lambda nome: obter_grau_risco(prolog, nome)
    )
    df["vizinhos_inadimplentes"]   = df["cliente_id"].apply(
        lambda nome: obter_num_vizinhos_inadimplentes(prolog, nome)
    )
    df["perfil_qualitativo"]       = df["cliente_id"].apply(
        lambda nome: obter_perfil_qualitativo(prolog, nome)
    )
    print("[OK] Features relacionais adicionadas ao DataFrame.")
    return df


# ---------------------------------------------------------------------------
#  SEÇÃO 3 — Treinamento do Classificador Estatístico
# ---------------------------------------------------------------------------

def treinar_modelo(df: pd.DataFrame):
    """
    Treina uma Regressão Logística combinando:
      - Features tradicionais : renda_mensal, score_classico
      - Feature relacional    : grau_risco_rede, vizinhos_inadimplentes
    Retorna o modelo treinado e as features usadas.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score

    FEATURES = ["renda_mensal", "score_classico",
                "grau_risco_rede", "vizinhos_inadimplentes"]
    TARGET   = "inadimplente_historico"

    X = df[FEATURES].copy()
    y = df[TARGET].copy()

    # Substitui 999 (sem conexão) por um valor alto mas finito para o scaler
    X["grau_risco_rede"] = X["grau_risco_rede"].replace(999, 10)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(max_iter=1000, random_state=42))
    ])
    pipeline.fit(X, y)

    # Validação cruzada (leave-one-out dado o dataset pequeno)
    scores = cross_val_score(pipeline, X, y, cv=min(5, len(df)),
                             scoring="accuracy")
    print(f"\n[*] Acurácia média (CV-{len(scores)}): "
          f"{scores.mean():.2%} ± {scores.std():.2%}")

    return pipeline, FEATURES


# ---------------------------------------------------------------------------
#  SEÇÃO 4 — Interpretabilidade (XAI): Exibição dos Coeficientes
# ---------------------------------------------------------------------------

def exibir_coeficientes(pipeline, feature_names: list):
    """
    Extrai os coeficientes da Regressão Logística e os apresenta de forma
    interpretável — núcleo da análise de XAI do projeto.
    """
    lr     = pipeline.named_steps["lr"]
    coefs  = lr.coef_[0]

    tabela = sorted(
        zip(feature_names, coefs),
        key=lambda x: abs(x[1]),
        reverse=True
    )

    print("\n" + "=" * 60)
    print("  COEFICIENTES DO MODELO (Regressão Logística)")
    print("  Valores positivos → aumentam probabilidade de inadimplência")
    print("  Valores negativos → reduzem probabilidade de inadimplência")
    print("=" * 60)
    print(tabulate(
        [(f, f"{c:+.4f}") for f, c in tabela],
        headers=["Feature", "Coeficiente"],
        tablefmt="fancy_grid"
    ))

    print("\n[XAI] Interpretação:")
    for feat, coef in tabela:
        sinal  = "aumenta" if coef > 0 else "reduz"
        print(f"  • '{feat}' (coef={coef:+.4f}): "
              f"quanto maior, mais {sinal} o risco predito.")


# ---------------------------------------------------------------------------
#  SEÇÃO 5 — Saída ProbLog-Style: Regras Probabilísticas Dinâmicas
# ---------------------------------------------------------------------------

def gerar_regras_problog(pipeline, df: pd.DataFrame,
                         feature_names: list, prolog) -> list:
    """
    Para cada cliente, calcula a probabilidade de inadimplência e formata
    uma regra estilo ProbLog com justificativa relacional extraída do Prolog.
    Retorna lista de strings com as regras geradas.
    """
    FEATURES_NUM = feature_names.copy()
    X_pred = df[FEATURES_NUM].copy()
    X_pred["grau_risco_rede"] = X_pred["grau_risco_rede"].replace(999, 10)

    probs = pipeline.predict_proba(X_pred)[:, 1]

    print("\n" + "=" * 60)
    print("  SAÍDA RELACIONAL-ESTATÍSTICA (Estilo ProbLog)")
    print("=" * 60)

    regras = []
    for i, row in df.iterrows():
        nome  = row["cliente_id"]
        prob  = probs[i]
        grau  = row["grau_risco_rede"]
        viz   = row["vizinhos_inadimplentes"]
        perfil = row["perfil_qualitativo"]

        grau_str = str(grau) if grau != 999 else "∞ (sem conexão)"

        if grau <= 1:
            justificativa = (
                f"conectado_direto({nome}, inadimplente)"
            )
        elif grau <= 3:
            justificativa = (
                f"conectado_grau({nome}, inadimplente, {grau})"
            )
        else:
            justificativa = (
                f"sem_conexao_relevante({nome})"
            )

        regra = (
            f"{prob:.2f} :: risco({nome}) :- "
            f"{justificativa}, "
            f"vizinhos_inadimplentes({nome}, {viz}), "
            f"perfil_simbolico({nome}, {perfil})."
        )
        regras.append(regra)
        print(f"  {regra}")

    return regras


# ---------------------------------------------------------------------------
#  SEÇÃO 6 — Relatório Final
# ---------------------------------------------------------------------------

def exibir_dataset_enriquecido(df: pd.DataFrame):
    """Exibe o DataFrame enriquecido com todas as features."""
    print("\n" + "=" * 60)
    print("  DATASET ENRIQUECIDO (Tradicional + Relacional)")
    print("=" * 60)
    colunas_exibir = [
        "cliente_id", "renda_mensal", "score_classico",
        "grau_risco_rede", "vizinhos_inadimplentes",
        "perfil_qualitativo", "inadimplente_historico"
    ]
    print(tabulate(
        df[colunas_exibir].values,
        headers=colunas_exibir,
        tablefmt="fancy_grid"
    ))


def salvar_regras_problog(regras: list, caminho: str = "regras_problog.pl"):
    """Persiste as regras ProbLog geradas em um arquivo .pl."""
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("% Regras ProbLog geradas automaticamente pelo pipeline SRL\n")
        f.write("% Disciplina ICC260 — IA: Da Lógica aos Números\n\n")
        for r in regras:
            f.write(r + "\n")
    print(f"\n[OK] Regras ProbLog salvas em '{caminho}'.")


# ---------------------------------------------------------------------------
#  MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  PIPELINE SRL — Risco de Crédito Híbrido")
    print("  ICC260 | Prof. Edjard Mota")
    print("=" * 60)

    # 1. Motor Prolog
    prolog = inicializar_prolog()

    # 2. Dados financeiros tradicionais
    df = pd.read_csv(CSV_FILE)
    print(f"[OK] Dataset '{CSV_FILE}' carregado: {len(df)} clientes.")

    # 3. Enriquecimento relacional via Prolog
    df = extrair_features_relacionais(prolog, df)
    exibir_dataset_enriquecido(df)

    # 4. Treinamento do classificador
    print("\n[*] Treinando Regressão Logística...")
    pipeline, features = treinar_modelo(df)
    print("[OK] Modelo treinado.")

    # 5. Análise XAI — coeficientes interpretáveis
    exibir_coeficientes(pipeline, features)

    # 6. Geração de regras ProbLog-style
    regras = gerar_regras_problog(pipeline, df, features, prolog)
    salvar_regras_problog(regras, "regras_problog_geradas.pl")

    print("\n[CONCLUÍDO] Pipeline SRL executado com sucesso.")


if __name__ == "__main__":
    main()
