% Núcleo lógico-topológico. Los hechos de infraestructura se inyectan desde Python.

% Un movimiento existe cuando un carril entrante permite un tipo de giro y existe
% un destino topológicamente/geometricamente válido para ese giro.
movement(I,L,From,To,T) :- lane(I,L,From), lane_allows(I,L,T), turn_target(I,From,T,To).

% Las trayectorias se expresan como ocupación de zonas geométricas neutrales.
% Clingo deriva el conflicto cuando dos movimientos legalmente existentes ocupan
% una misma zona interna o de convergencia. Python no entrega pares conflictivos.
conflict(I,L1,T1,L2,T2) :- movement(I,L1,_,T1,_), movement(I,L2,_,T2,_),
                            occupies(I,L1,T1,Z), occupies(I,L2,T2,Z), L1 != L2.
conflict(I,L2,T2,L1,T1) :- conflict(I,L1,T1,L2,T2).

% Dos movimientos que salen desde el mismo carril hacia destinos distintos no se
% ejecutan simultáneamente; comparten el mismo recurso de aproximación.
conflict(I,L,T1,L,T2) :- movement(I,L,_,T1,_), movement(I,L,_,T2,_), T1 != T2.

% Cada intersección puede usar como máximo tantos IDs de fase como movimientos.
movement_count(I,N) :- intersection(I), N = #count { L,To : movement(I,L,_,To,_) }.
phase_id(I,1..N) :- movement_count(I,N), N > 0.

% Cada movimiento pertenece exactamente a una fase.
1 { in_phase(I,L,To,P) : phase_id(I,P) } 1 :- movement(I,L,_,To,_).
used_phase(I,P) :- in_phase(I,_,_,P).

% Una fase nunca contiene movimientos conflictivos.
:- conflict(I,L1,T1,L2,T2), in_phase(I,L1,T1,P), in_phase(I,L2,T2,P).

% Rompe simetría: si se usa P>1, también se usa P-1.
:- used_phase(I,P), P > 1, P0 = P-1, not used_phase(I,P0).

% Minimiza el número total de fases usadas.
#minimize { 1@1,I,P : used_phase(I,P) }.

#show movement/5.
#show conflict/5.
#show in_phase/4.
#show used_phase/2.

% Señal lógica asociada a cada movimiento controlado.
signal(I,L,To) :- movement(I,L,_,To,_).
controlled(I,L,To) :- signal(I,L,To).
#show signal/3.
#show controlled/3.
