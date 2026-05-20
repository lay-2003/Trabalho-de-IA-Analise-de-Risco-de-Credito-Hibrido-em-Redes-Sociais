% ===========================================================================
%  rede_social.pl — Base de Conhecimento Relacional
% ===========================================================================

:- use_module(library(lists)).

% ---------------------------------------------------------------------------
%  SEÇÃO 1 — FATOS: Transações Financeiras Diretas
%  transacao_entre(+Origem, +Destino, +Valor)
% ---------------------------------------------------------------------------

transacao_entre(joao,    ana,     1500).
transacao_entre(ana,     carlos,   800).
transacao_entre(carlos,  daniel,    50).
transacao_entre(ana,     eva,      300).
transacao_entre(eva,     felix,    950).
transacao_entre(felix,   daniel,   120).   % felix também conectado ao inadimplente
transacao_entre(gabriel, ana,      450).
transacao_entre(helena,  carlos,   200).
transacao_entre(igor,    helena,   670).
transacao_entre(joao,    gabriel, 2200).

% ---------------------------------------------------------------------------
%  SEÇÃO 2 — FATOS: Histórico de Inadimplência Clássico
% ---------------------------------------------------------------------------

inadimplente(daniel).
inadimplente(carlos).   % carlos também marcado como inadimplente no histórico

% ---------------------------------------------------------------------------
%  SEÇÃO 3 — FATOS: Atributos Individuais
%  renda(+Pessoa, +ValorMensal)
%  score_credito(+Pessoa, +Pontuacao)
% ---------------------------------------------------------------------------

renda(joao,    5200).
renda(ana,     3100).
renda(carlos,  1800).
renda(daniel,   900).
renda(eva,     4200).
renda(felix,   2700).
renda(gabriel, 6100).
renda(helena,  3800).
renda(igor,    5500).

score_credito(joao,    750).
score_credito(ana,     610).
score_credito(carlos,  420).
score_credito(daniel,  310).
score_credito(eva,     690).
score_credito(felix,   540).
score_credito(gabriel, 800).
score_credito(helena,  580).
score_credito(igor,    720).

% ---------------------------------------------------------------------------
%  SEÇÃO 4 — REGRAS: Conectividade Bidirecional
%  conectado(+A, +B) — verdadeiro se existe transação em qualquer direção
% ---------------------------------------------------------------------------

conectado(X, Y) :- transacao_entre(X, Y, _).
conectado(X, Y) :- transacao_entre(Y, X, _).

% ---------------------------------------------------------------------------
%  SEÇÃO 5 — REGRAS: Propagação de Risco por Grau de Separação (Recursiva)
%  risco_conexao(+X, +Y, -Grau)
%  Calcula o menor grau de separação entre X e qualquer inadimplente Y.
%  Grau 1 = conexão direta; Grau 2 = um intermediário; etc.
% ---------------------------------------------------------------------------

% Caso base: conexão direta (grau 1)
risco_conexao(X, Y, 1) :-
    conectado(X, Y),
    inadimplente(Y).

% Caso recursivo: via intermediário Z
risco_conexao(X, Y, Grau) :-
    conectado(X, Z),
    Z \= Y,            % evita ciclos triviais
    risco_conexao(Z, Y, GrauAnterior),
    Grau is GrauAnterior + 1.

% ---------------------------------------------------------------------------
%  SEÇÃO 6 — REGRAS: Grau Mínimo de Risco (ignora caminhos mais longos)
%  grau_minimo_risco(+X, -GrauMin)
%  Retorna o menor grau de exposição de X a qualquer inadimplente.
% ---------------------------------------------------------------------------

grau_minimo_risco(X, GrauMin) :-
    findall(G, (inadimplente(Y), risco_conexao(X, Y, G)), Graus),
    Graus \= [],
    min_list(Graus, GrauMin).

grau_minimo_risco(X, 999) :-
    \+ (inadimplente(Y), risco_conexao(X, Y, _)),
    renda(X, _).  % pessoa existe na base mas sem conexão com inadimplente

% ---------------------------------------------------------------------------
%  SEÇÃO 7 — REGRAS: Contagem de Vizinhos Inadimplentes (1º grau)
%  num_vizinhos_inadimplentes(+X, -N)
% ---------------------------------------------------------------------------

num_vizinhos_inadimplentes(X, N) :-
    findall(Y, (conectado(X, Y), inadimplente(Y)), Ys),
    length(Ys, N).

% ---------------------------------------------------------------------------
%  SEÇÃO 8 — REGRAS: Perfil de Risco Composto
%  perfil_risco(+X, -Nivel)
%  Classifica em alto_risco, medio_risco ou baixo_risco com base em
%  lógica simbólica pura (base para interpretação qualitativa).
% ---------------------------------------------------------------------------

perfil_risco(X, alto_risco) :-
    inadimplente(X), !.

perfil_risco(X, alto_risco) :-
    grau_minimo_risco(X, Grau),
    Grau =< 1,
    score_credito(X, Score),
    Score < 500.

perfil_risco(X, medio_risco) :-
    grau_minimo_risco(X, Grau),
    Grau =< 2,
    score_credito(X, Score),
    Score < 650.

perfil_risco(X, baixo_risco) :-
    grau_minimo_risco(X, Grau),
    (Grau >= 3 ; Grau =:= 999),
    score_credito(X, Score),
    Score >= 650.

perfil_risco(X, medio_risco) :-
    renda(X, _),
    \+ perfil_risco(X, alto_risco),
    \+ perfil_risco(X, baixo_risco).

% ---------------------------------------------------------------------------
%  FIM DA BASE — rede_social.pl
% ---------------------------------------------------------------------------
