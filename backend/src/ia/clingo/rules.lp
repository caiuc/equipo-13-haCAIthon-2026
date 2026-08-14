% Núcleo lógico-topológico. Los hechos de infraestructura se inyectan desde Python.

movement(I,L,From,To,T) :- lane(I,L,From), lane_allows(I,L,T), turn_target(I,From,T,To).

% Dos movimientos rectos opuestos son compatibles: circulan en pistas paralelas
% del mismo eje. Esta excepción evita convertir el cruce simple N/S + E/O en
% cuatro fases artificiales por compartir zonas geométricas discretizadas.
opposite_straights(I,L1,T1,L2,T2) :-
    movement(I,L1,F1,T1,straight), movement(I,L2,F2,T2,straight),
    F1 = T2, F2 = T1, L1 != L2.

conflict(I,L1,T1,L2,T2) :-
    movement(I,L1,_,T1,_), movement(I,L2,_,T2,_),
    occupies(I,L1,T1,Z), occupies(I,L2,T2,Z), L1 != L2,
    not opposite_straights(I,L1,T1,L2,T2).
conflict(I,L2,T2,L1,T1) :- conflict(I,L1,T1,L2,T2).

% Un mismo carril no puede ejecutar destinos diferentes simultáneamente.
conflict(I,L,T1,L,T2) :- movement(I,L,_,T1,_), movement(I,L,_,T2,_), T1 != T2.

movement_count(I,N) :- intersection(I), N = #count { L,To : movement(I,L,_,To,_) }.
phase_id(I,1..N) :- movement_count(I,N), N > 0.

1 { in_phase(I,L,To,P) : phase_id(I,P) } 1 :- movement(I,L,_,To,_).
used_phase(I,P) :- in_phase(I,_,_,P).

:- conflict(I,L1,T1,L2,T2), in_phase(I,L1,T1,P), in_phase(I,L2,T2,P).
:- used_phase(I,P), P > 1, P0 = P-1, not used_phase(I,P0).

#minimize { 1@1,I,P : used_phase(I,P) }.

#show movement/5.
#show conflict/5.
#show in_phase/4.
#show used_phase/2.
