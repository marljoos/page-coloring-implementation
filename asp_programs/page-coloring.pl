%  Gegeben ist:
%  1. Eine endliche Menge von Subjects, Kernels und eine endliche Menge von Channels für die gilt:
%     - R1: Subjects und Kernels sind Executors.
%     - R2: Subjects und Kernels sind MemoryRegions.
%     - R3: Ein Channel besteht aus einem Quell-Executor (FROM) und einem Ziel-Executor (TO)
%           und ist selbst ein eigener MemoryRegion. 
%  2. Eine endliche Menge von CPUs CPUS = cpu_1, ..., cpu_n.
%  3. Das zweistellige Prädikat
%     ex_cpu(X, Y) : (Executors, CPUS) -> Bool, für das gilt:
%     - R1: Jedem Executor X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen.
%     	- Z. B. (ex_1, [cpu_1]), (ex_2, [cpu_2, cpu_3]), ..., (ex_n, [cpu_4]).
%     - R2: Jeder CPU muss mindestens ein Executor zugeordnet worden sein.
%     - R3: Aus R1 und R2 wird das zweistellige Prädikat
%           mr_cpu(X, Y) : (MemoryRegion, CPUS) -> Bool abgeleitet, für das gilt:
%           - R3.1: Executor-CPU entspricht der MemoryRegion-CPU: ex_cpu(X, Y) => mr_cpu(X, Y)
%           - R3.2: Zuordnung der CPUs des Lesers (TO) und des Schreibers (FROM) zum MemoryRegion eines Channels.
%                   (Gegeben Channel channel(X, Y), wobei X einer CPU X_CPU und Y einer CPU Y_CPU zugeordnet wurde:
%                   mr_cpu(X, X_CPU) und mr_cpu(X, Y_CPU), dann wird dem MemoryRegion des Channels
%                   memory_region(c(X, Y)) ebenfalls die CPUs zugeordnet:
%                   mr_cpu(c(X, Y), X_CPU) und mr_cpu(c(X, Y), Y_CPU).
%           - R3.3: Jedem MemoryRegion X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen.
%           - R3.4: Jeder CPU muss mindestens ein MemoryRegion zugeordnet worden sein.
%  4. Eine endliche Menge von CacheColors pro Level (wir gehen hier von 3 Level aus).
%     - Eine CacheColor besteht aus einer Cache-Id und optional aus einer CPU.
%     - Dabei sind alle Farben eines Caches-Levels entweder einer CPU gebunden oder nicht
%       (aber nicht gemischt).
%     - Z. B. alle Cache-Farben eines Systems:
%       - L1-Farben (CPU gebunden):				{ l1_color(X, Y) | X ∈ 1..2, Y ∈ CPUS }
%       - L2-Farben (CPU gebunden):				{ l2_color(X, Y) | X ∈ 1..4, Y ∈ CPUS }
%       - L3-Farben (an keine CPU gebunden):	{ l3_color(X) 	 | X ∈ 1..8 }
%  5. Eine endliche Menge von PageColors.
%     - Eine PageColor besteht aus jeweils einer Farbe aus jeweils eine der Cache-Levels,
%       und verknüpft diese miteinander.
%     - Z. B. eine PageColor: page_colors(l1_color(2, 1), l2_color(3, 1), l3_color(2)).
%  6. Eine endliche Menge von CacheIsolationDomains, um MemoryRegions, die im Cache interferieren
%     dürfen, zu spezifizieren (gleiche CacheIsolationDomain), als auch MemoryRegion, die nicht 
%     im Cache interferieren dürfen, zu spezifizieren (unterschiedliche CacheIsolationDomain).
%  7. Das zweistellige Prädikat
%     mr_cache_isolation(X, Y) : (MemoryRegions, CacheIsolationsDomain) -> Bool, für das gilt:
%     - R1: Jedem MemoryRegion X wird genau eine CacheIsolationDomain Y zugeordnet.
%     	- Z. B. bei N=4 MemoryRegions; zwei MemoryRegions zusammen in jeweils zwei
%     	  Cache-Isolationsdomänen:
%	  	  - mr_cache_isolation(mr_1, 1)
%	  	  - mr_cache_isolation(mr_2, 1)
%	  	  - mr_cache_isolation(mr_3, 2)
%	  	  - mr_cache_isolation(mr_4, 2)
%     - R2: Jeder CacheIsolationDomain wurde mindestens ein MemoryRegion zugeordnet.
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% 8. Gesucht ist das Prädikat
%    map_pc(X,Y) : (MemoryRegion, PageColors) -> Bool, für das gilt:
%    - R1: Jedem MemoryRegion X wird eine oder mehrere PageColors ∈ 𝒫 ⁺(PageColors) zugewiesen.
%    - R2: Beachtung aller CPUs eines MemoryRegions:
%          Wenn MemoryRegion X, den CPUs X_CPUS ∈ 𝒫 ⁺(CPUS)
%          zugeordnet wurde, dann ordne X für jede CPU von X X_CPU ∈ X_CPUS, |X_CPUS| = N
%          die PageColors
%          page_color(L1_1, L2_1, L3_1), ..., page_color(IDN, L1_N, L2_N, L3_N) zu,
%          sodass die Cache-Ids aller PageColors übereinstimmen, und pro PageColor
%		   eine X_CPU ausgewählt wird und die CPUs der CacheColors bestimmt.
%    - R3: Vermeidung von Interferenz im L3-Cache:
%          Wenn MemoryRegion A und MemoryRegion B sich in unterschiedlichen Cache-
%          Isolationsdomänen befinden, dann gilt paarweise für jede
%          PageColor-Zuordnung von A
%          map_pc(A, page_color(l1_color(_, _), l2_color(_, _), l3_color(L3_A))),
%          und für jede PageColor-Zuordnung von B
%          map_pc(B, page_color(l1_color(_, _), l2_color(_, _), l3_color(L3_B))),
%          L3_A ≠ L3_B .
%    - R4: Vermeidung von Interferenz im L2-Cache:
%          Wenn MemoryRegion A und MemoryRegion B sich in unterschiedlichen Cache-
%          Isolationsdomänen befinden, und auf der gleichen CPU Cpu ausgeführt werden
%          (d. h. mr_cpu(A, Cpu) und mr_cpu(B, Cpu)), dann gilt paarweise für jede
%          PageColor-Zuordnung von A
%          map_pc(A, page_color(l1_color(_, _), l2_color(L2_A, Cpu), l3_color(_))),
%          und für jede PageColor-Zuordnung von B
%          map_pc(B, page_color(l1_color(_, _), l2_color(L2_B, Cpu), l3_color(_))) :
%          L2_A != L2_B .
%    - R5: Optimierung: Verteile möglichst alle Cache-Farben.
%          Priorisiere in absteigender Reihenfolge L3-Farben, L2-Farben, L1-Farben.
%    - R6: TODO: Performanz-Constraints
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%  1. Eine endliche Menge von Subjects, Kernels und eine endliche Menge von Channels für die gilt:

% TODO: Ggf. ein Constraint hinzufügen, um zu verhindern, dass ein X für mehrere MemoryRegion-Arten definiert wird.

%     - R1: Subjects und Kernels sind Executors.
% Executor haben die Eigenschaft, dass sie auf ein oder mehrere CPUs ausgeführt werden können.
executor(X) :- kernel(X).
executor(X) :- subject(X).

%     - R2: Subjects und Kernels sind MemoryRegions.
memory_region(X) :- kernel(X).
memory_region(X) :- subject(X).

%     - R3: Ein Channel besteht aus einem Quell-Executor (FROM) und einem Ziel-Executor (TO)
%           und ist selbst ein eigener MemoryRegion. 
memory_region(c(FROM,TO)) :- channel(FROM, TO), executor(FROM), executor(TO).

%  2. Eine endliche Menge von CPUs CPUS = cpu_1, ..., cpu_n.

%  3. Das zweistellige Prädikat
%     ex_cpu(X, Y) : (Executors, CPUS) -> Bool, für das gilt:


%     - R1: Jedem Executor X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen.
%     	- Z. B. (ex_1, [cpu_1]), (ex_2, [cpu_2, cpu_3]), ..., (ex_n, [cpu_4]).
% D. h. es kann nicht der Fall sein, dass es ein Executor X gibt, und X keine CPU
% zugeordnet wurde.
:- executor(X), not ex_cpu(X,CPU) : cpu(CPU).

%     - R2: Jeder CPU muss mindestens ein Executor zugeordnet worden sein.
% D. h. es kann nicht der Fall sein, dass es eine CPU X gibt, und keine Zuordnung zu dieser
% existiert.
:- cpu(X), not ex_cpu(MC, X) : executor(MC).

%     - R3: Aus R1 und R2 wird das zweistellige Prädikat
%           mr_cpu(X, Y) : (MemoryRegion, CPUS) -> Bool abgeleitet, für das gilt:
%           - R3.1: Executor-CPU entspricht der MemoryRegion-CPU: ex_cpu(X, Y) => mr_cpu(X, Y)
mr_cpu(MC, CPU) :- ex_cpu(MC, CPU).

%           - R3.2: Zuordnung der CPUs des Lesers (TO) und des Schreibers (FROM) zum MemoryRegion eines Channels.
%                   (Gegeben Channel channel(X, Y), wobei X einer CPU X_CPU und Y einer CPU Y_CPU zugeordnet wurde:
%                   mr_cpu(X, X_CPU) und mr_cpu(X, Y_CPU), dann wird dem MemoryRegion des Channels
%                   memory_region(c(X, Y)) ebenfalls die CPUs zugeordnet:
%                   mr_cpu(c(X, Y), X_CPU) und mr_cpu(c(X, Y), Y_CPU).
mr_cpu(c(X,Y), CPU) :- channel(X,Y), mr_cpu(X, CPU).
mr_cpu(c(X,Y), CPU) :- channel(X,Y), mr_cpu(Y, CPU).

%           - R3.3: Jedem MemoryRegion X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen.
% D. h. es kann nicht der Fall sein, dass es ein MemoryRegion X gibt, und X keine CPU
% zugeordnet wurde.
%:- memory_region(X), 0 { mr_cpu(X,CPU) : cpu(CPU) } 0.
:- memory_region(X), not mr_cpu(X,CPU) : cpu(CPU).

%           - R3.4: Jeder CPU muss mindestens ein MemoryRegion zugeordnet worden sein.
% D. h. es kann nicht der Fall sein, dass es eine CPU X gibt, und keine Zuordnung zu dieser
% existiert.
%:- cpu(X), 0 { mr_cpu(MC, X) : memory_region(MC) } 0.
:- cpu(X), not mr_cpu(MC, X) : memory_region(MC).

%  4. Eine endliche Menge von CacheColors pro Level (wir gehen hier von 3 Level aus).
%     - Eine CacheColor besteht aus einer Cache-Id und optional aus einer CPU.
%     - Dabei sind alle Farben eines Caches-Levels entweder einer CPU gebunden oder nicht
%       (aber nicht gemischt).
%     - Z. B. alle Cache-Farben eines Systems:
%       - L1-Farben (CPU gebunden):				{ l1_color(X, Y) | X ∈ 1..2, Y ∈ CPUS }
%       - L2-Farben (CPU gebunden):				{ l2_color(X, Y) | X ∈ 1..4, Y ∈ CPUS }
%       - L3-Farben (an keine CPU gebunden):	{ l3_color(X) 	| X ∈ 1..8 }

%  5. Eine endliche Menge von PageColors.
%     - Eine PageColor besteht aus jeweils einer Farbe aus jeweils eine der Cache-Levels,
%       und verknüpft diese miteinander.

% TODO: Ggf. ein Constraint hinzufügen, um sicherzustellen,
% dass alle CacheColors verwendet werden.


%  6. Eine endliche Menge von CacheIsolationDomains, um MemoryRegions, die im Cache interferieren
%     dürfen, zu spezifizieren (gleiche CacheIsolationDomain), als auch MemoryRegion, die nicht 
%     im Cache interferieren dürfen, zu spezifizieren (unterschiedliche CacheIsolationDomain).


%  7. Das zweistellige Prädikat
%     mr_cache_isolation(X, Y) : (MemoryRegions, CacheIsolationsDomain) -> Bool, für das gilt:


%     - R1: Jedem MemoryRegion X wird genau eine CacheIsolationDomain Y zugeordnet.
% D. h. es kann nicht der Fall sein, dass es ein MemoryRegion X gibt, und dieser nicht genau
% einer mr_cache_isolation(X,Y)-Zuordnung zu einer CacheIsolationDomain Y besitzt.
:- memory_region(X), not 1 {mr_cache_isolation(X,Y): cache_isolation_domain(Y)} 1.

%     - R2: Jeder CacheIsolationDomain wurde mindestens ein MemoryRegion zugeordnet.
% D. h. es kann nicht der Fall sein, dass eine CacheIsolationDomain X existiert, die keine
% mr_cache_isolation(Y,X)-Zuordnung zu einem MemoryRegion Y besitzt.
:- cache_isolation_domain(X), 0 {mr_cache_isolation(MC,X): memory_region(MC)} 0.

% 8. Gesucht ist das Prädikat
%    map_pc(X,Y) : (MemoryRegion, PageColors) -> Bool, für das gilt:
%    - R1: Jedem MemoryRegion X wird eine oder mehrere PageColors ∈ 𝒫 ⁺(PageColors) zugewiesen.
1 { map_pc(X, page_color(l1_color(A, CPU), l2_color(B, CPU), l3_color(C)))
	: page_color(l1_color(A, CPU), l2_color(B, CPU), l3_color(C)) }
	:- memory_region(X), mr_cpu(X, CPU).

%    - R2: Beachtung aller CPUs eines MemoryRegions:
%          Wenn MemoryRegion X, den CPUs X_CPUS ∈ 𝒫 ⁺(CPUS)
%          zugeordnet wurde, dann ordne X für jede CPU von X X_CPU ∈ X_CPUS, |X_CPUS| = N
%          die PageColors
%          page_color(L1_1, L2_1, L3_1), ..., page_color(IDN, L1_N, L2_N, L3_N) zu,
%          sodass die Cache-Ids aller PageColors übereinstimmen, und pro PageColor
%		   eine X_CPU ausgewählt wird und die CPUs der CacheColors bestimmt.
{	map_pc(page_color(l1_color(A, OTHER_CPU), l2_color(B, OTHER_CPU), l3_color(C)))
	 : mr_cpu(X, OTHER_CPU), OTHER_CPU != X_CPU
}
	:- memory_region(X),
   	   mr_cpu(X, X_CPU),
	   map_pc(X, page_color(l1_color(A, X_CPU), l2_color(B, X_CPU), l3_color(C))).

%    - R3: Vermeidung von Interferenz im L3-Cache:
%          Wenn MemoryRegion A und MemoryRegion B sich in unterschiedlichen Cache-
%          Isolationsdomänen befinden, dann gilt paarweise für jede
%          PageColor-Zuordnung von A
%          map_pc(A, page_color(l1_color(_, _), l2_color(_, _), l3_color(L3_A))),
%          und für jede PageColor-Zuordnung von B
%          map_pc(B, page_color(l1_color(_, _), l2_color(_, _), l3_color(L3_B))),
%          L3_A ≠ L3_B .
A_L3 != B_L3
	:- memory_region(A), memory_region(B),
	   A != B,
	   mr_cache_isolation(A, CI1), mr_cache_isolation(B, CI2),
	   CI1 != CI2,
	   map_pc(A, page_color(l1_color(_, _), l2_color(_, _), l3_color(A_L3))),
	   map_pc(B, page_color(l1_color(_, _), l2_color(_, _), l3_color(B_L3))).

%    - R4: Vermeidung von Interferenz im L2-Cache:
%          Wenn MemoryRegion A und MemoryRegion B sich in unterschiedlichen Cache-
%          Isolationsdomänen befinden, und auf der gleichen CPU Cpu ausgeführt werden
%          (d. h. mr_cpu(A, Cpu) und mr_cpu(B, Cpu)), dann gilt paarweise für jede
%          PageColor-Zuordnung von A
%          map_pc(A, page_color(l1_color(_, _), l2_color(L2_A, Cpu), l3_color(_))),
%          und für jede PageColor-Zuordnung von B
%          map_pc(B, page_color(l1_color(_, _), l2_color(L2_B, Cpu), l3_color(_))) :
%          L2_A != L2_B .
A_L2 != B_L2
	:- memory_region(A), memory_region(B),
	   A != B,
	   mr_cache_isolation(A, CI1), mr_cache_isolation(B, CI2),
	   CI1 != CI2,
	   mr_cpu(A, CPU), mr_cpu(B, CPU),
	   map_pc(A, page_color(l1_color(_, _), l2_color(A_L2, CPU), l3_color(_))),
	   map_pc(B, page_color(l1_color(_, _), l2_color(B_L2, CPU), l3_color(_))).

%    - R5: Optimierung: Verteile möglichst alle Cache-Farben.
%          Priorisiere in absteigender Reihenfolge L3-Farben, L2-Farben, L1-Farben.
#maximize { 4, l3_color(X)	: map_pc(_, page_color(_, _, l3_color(X))) }.
#maximize { 2, l2_color(X, Y)	: map_pc(_, page_color(_, l2_color(X, Y), _)) }.
#maximize { 1, l1_color(X, Y)	: map_pc(_, page_color(l1_color(X, Y), _, _)) }.

% Für das Debugging: Ausgabe der Anzahl der verteilten Farben pro Cache-Level.
mapped(L1) :- map_pc(_, page_color(L1, _, _)).
mapped(L2) :- map_pc(_, page_color(_, L2, _)).
mapped(L3) :- map_pc(_, page_color(_, _, L3)).

l3_count(N) :- #count {X : mapped(l3_color(X)) } = N.
l2_count(N) :- #count {l2_color(X, Y) : mapped(l2_color(X, Y)) } = N.
l1_count(N) :- #count {l1_color(X, Y) : mapped(l1_color(X, Y)) } = N.
