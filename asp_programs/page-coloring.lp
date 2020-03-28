%  Gegeben ist:
%  1. Eine endliche Menge von benannten Subjects, Kernels und Channels für die gilt:
%     - 1.1: Subjects und Kernels sind Executors.
%     - 1.2: Subjects, Kernels und Channels sind MemoryRegions.
%     - 1.3: Ein Channel besitzt genau ein Executor, der zum Channel schreiben kann (Writer).
%           - Ausgedrückt durch: writes_to(executor(WRITER_NAME), channel(CHANNEL_NAME)).
%     - 1.4: Ein Channel besitzt ein oder mehrere Executors, die vom Channel lesen können (Readers).
%           - Ausgedrückt durch:
%             - reads_from(executor(READER_NAME_1), channel(CHANNEL_NAME)).
%             - reads_from(executor(READER_NAME_2), channel(CHANNEL_NAME)).
%             - ...
%             - reads_from(executor(READER_NAME_N), channel(CHANNEL_NAME)).
%  2. Eine endliche Menge von N CPUs : CPUS = cpu(1..N).
%  3. Das zweistellige Prädikat
%     ex_cpu(executor(X), cpu(Y)) : (Executors, CPUS) -> Bool, für das gilt:
%     - 3.1: Jedem Executor X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen.
%     	- Z. B.
%         - (ex_1, [cpu_1])         -> ex_cpu(executor(EX_1), cpu(1)).
%         - (ex_2, [cpu_2, cpu_3])  -> ex_cpu(executor(EX_2), cpu(2)). ex_cpu(executor(EX_2), cpu(3)).
%         - ...
%         - (ex_n, [cpu_4]).        -> ex_cpu(executor(EX_N), cpu(4)).
%     - 3.2: Jeder CPU muss mindestens ein Executor zugeordnet worden sein.
%     - 3.3: Aus 3.1 und 3.2 wird das zweistellige Prädikat
%             mr_cpu(memory_region(X), cpu(Y)) : (MemoryRegions, CPUS) -> Bool abgeleitet, für das gilt:
%             - 3.3.1: Executor-CPU entspricht der MemoryRegion-CPU:
%                       - ex_cpu(executor(X), cpu(Y)) => mr_cpu(memory_region(X), cpu(Y)).
%             - 3.3.2: Zuordnung der CPUs des Writer oder des/der Reader(s) eines Channels zur MemoryRegion des
%                       Channels.
%                      - 3.3.2.1: Für Writer: Wenn writes_to(executor(EX), Channel(C)) und
%                                 ex_cpu(executor(EX), cpu(CPU)), dann: mr_cpu(memory_region(C), cpu(CPU)).
%                      - 3.3.2.2: Für Reader(s): Wenn reads_from(executor(EX), Channel(C)) und
%                                 ex_cpu(executor(EX), cpu(CPU)), dann: mr_cpu(memory_region(C), cpu(CPU).
%             - 3.3.3: Jedem MemoryRegion X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen. D. h. es gibt keine
%                      MemoryRegion, der keine CPU zugeordnet wurde.
%             - 3.3.4: Jeder CPU muss mindestens ein MemoryRegion zugeordnet worden sein. ANNAHME: D. h. wir nehmen an,
%                      dass jede CPU benutzt wird.
%  4. Das zweistellige Prädikat
%     mr_min_page_colors(memory_region(X), I) : (MemoryRegions, Positives) -> Bool, für das gilt:
%     - 4.1: Für jede MemoryRegion wird die Mindest-Anzahl der zu verteilenden PageColors an diese MemoryRegion
%            spezifiziert. D. h. es gibt keine MemoryRegion für die keine Mindest-Anzahl definiert wurde.
%            ANNAHME: I > 0 (Wir wollen immer mindestens eine PageColor verteilen können).
%  5. Eine endliche Menge von N Cache-Levels : Levels = level(1..N).
%  6. Das zweistellige Prädikat
%     cache_is_cpu_bound(level(X), Y). : (Levels, {yes, no}) -> Bool, für das gilt:
%     - 6.1: Für jedes Level des Caches (üblicherweise drei Level) wird spezifiziert, ob die Caches dieses Levels an
%            eine CPU gebunden sind oder nicht. ANNAHME: Wird nehmen hier an, dass ein Cache entweder an genau eine
%            CPU gebunden ist oder nicht. D. h. ein Cache, der an zwei CPUs gebunden ist, kann noch nicht modelliert
%            werden.
%  7. Eine endliche Menge von CacheColors pro Level (wir gehen hier von 3 Level aus).
%     - Eine CacheColor besteht aus einem Cache-Level (aus Levels) und einem Cache-Index (Integer).
%       - Z. B. cache_color(level(1), 2).
%  8. Eine endliche Menge von PageColors.
%     - Eine PageColor besteht aus jeweils einer Farbe aus jeweils eine der Cache-Levels,
%       und verknüpft diese miteinander.
%     - Z. B. eine PageColor: page_color(cache_color(level(1),1),cache_color(level(2),7),cache_color(level(3),55)).
%  9. Eine endliche Menge von N Cache-Isolationsdomänen : CacheIsolationDomains = cache_isolation_domain(1..N).
%     - Diese sind dazu da, um zu spezifizieren, welche MemoryRegions sich im Cache interferieren dürfen (gleiche
%       Cache-Isolationsdomäne), und welche MemoryRegions sich nicht im Cache interferieren dürfen (ungleiche Cache-
%       Isolationsdomäne).
% 10. Das zweistellige Prädikat
%     mr_cache_isolation(memory_region(X), cache_isolation_domain(Y)) : (MemoryRegions, CacheIsolationsDomains) -> Bool,
%     für das gilt:
%     - 10.1: Jedem MemoryRegion X wird genau eine CacheIsolationDomain Y zugeordnet.
%     	- Z. B. bei N=4 MemoryRegions; zwei MemoryRegions zusammen in jeweils zwei
%     	  Cache-Isolationsdomänen:
%	  	  - mr_cache_isolation(memory_region(mr_1), cache_isolation_domain(1)).
%	  	  - mr_cache_isolation(memory_region(mr_2), cache_isolation_domain(1)).
%	  	  - mr_cache_isolation(memory_region(mr_3), cache_isolation_domain(2)).
%	  	  - mr_cache_isolation(memory_region(mr_4), cache_isolation_domain(2)).
%     - 10.2: Jeder CacheIsolationDomain wurde mindestens eine MemoryRegion zugeordnet.
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% 11. Aus den Anforderungen von 1. bis einschließlich 10. werden zwei Prädikate abgeleitet, zum einen das Prädikat:
%     mr_pc(memory_region(X), page_color(...)) : (MemoryRegion, PageColors) -> Bool, das MemoryRegions die PageColors
%       verteilt, und zum anderen das Prädikat:
%     mr_spc(memory_region(X), system_page_color(cpu(CPU), page_color(...))) : (MemoryRegion, SystemPageColors) -> Bool,
%       das MemoryRegions die SystemPageColors verteilt, d. h. auch die CPUs mitbetrachten, die beim Zugriff auf die
%       MemoryRegions verwendet werden.
%     Für die Prädikate gelten:
%     - 11.1: Jeder MemoryRegion X werden mindestens so viel PageColors zugewiesen, wie durch
%             mr_min_page_colors(memory_region(X), I) spezifiziert wird.
%     - 11.2: Beachtung aller CPUs einer MemoryRegions:
%             Wenn MemoryRegion X, den CPUs X_CPUS ∈ 𝒫 ⁺(CPUS) und den PageColors P1, P2, P3, ... zugeordnet wurde,
%             dann ordne X für jede CPU von X X_CPU ∈ X_CPUS die SystemPageColors
%             system_page_color(cpu(X_CPU), P1), system_page_color(cpu(X_CPU), P2),
%             system_page_color(cpu(X_CPU), P3), ... zu.
%     %- 11.3: Erlaubnis der Interferenz innerhalb einer Cache-Isolationsdomäne:
%     %        Wenn MR X in CI Y und hat PageColor Z, und MR A auch in CI Y, dann gebe Y PageColor Z mit Y's CPUs.
%     %        Wenn MemoryRegion A und MemoryRegion B sich in der gleichen Cache-Isolationsdomäne X befinden und
%     %        MemoryRegion A der einer PageColor zugeordnet wurde, d. h.
%     %        map_pc(A, page_color(l1_color(L1, _), l2_color(L2, _), l3_color(L3_A))),
%     %        dann bekommt MemoryRegion B ebenfalls die PageColor zugewiesen, wobei aber die CPU-Ids der CPUs von B
%     %        übereinstimmen muss, d. h.:
%     %        map_pc(B, page_color(cache_color(level(1), L1), cache_color(level(2), L2), cache_color(level(3), L3)) und mr_cpu(B, CPU).
%     - 11.4: Vermeidung von Interferenz im Cache:
%             Die Vermeidung von Interferenz im Cache ist abhängig davon, ob der Cache CPU-gebunden ist oder nicht.
%             Ist der Cache CPU-gebunden, dann muss die Verteilung der SystemPageColors betrachtet werden, ist der Cache
%             nicht CPU-gebunden, dann muss die Verteilung der PageColors betrachtet werden.
%             - 11.4.1: Vermeidung von Interferenz im L3-Cache:
%                       - 11.4.1.1: Falls L3 nicht CPU-gebunden ist:
%                                   Wenn MemoryRegion A und MemoryRegion B (und A!=B) sich in unterschiedlichen Cache-
%                                   Isolationsdomänen befinden, dann gilt paarweise für jede
%                                   PageColor-Zuordnung von A
%                                   mr_pc(A, page_color(cache_color(level(1), L1), cache_color(level(2), L2),
%                                     cache_color(level(3), L3_A)),
%                                   und für jede PageColor-Zuordnung von B
%                                   mr_pc(memory_region(B), page_color(cache_color(level(1), L1),
%                                     cache_color(level(2), L2), cache_color(level(3), L3_B))
%                                   folgendes:
%                                   L3_A ≠ L3_B .
%                       - 11.4.1.2: Falls L3 CPU-gebunden ist:
%                                   Wenn MemoryRegion A und MemoryRegion B (und A!=B) sich in unterschiedlichen Cache-
%                                   Isolationsdomänen befinden, dann gilt paarweise für jede
%                                   SystemPageColor-Zuordnung von A
%                                   mr_spc(memory_region(A), system_page_color(cpu(CPU_A),
%                                     page_color(cache_color(level(1), L1), cache_color(level(2), L2),
%                                     cache_color(level(3), L3_A))),
%                                   und für jede PageColor-Zuordnung von B
%                                   mr_spc(memory_region(B), system_page_color(cpu(CPU_B),
%                                     page_color(cache_color(level(1), L1), cache_color(level(2), L2),
%                                     cache_color(level(3), L3_B))),
%                                   folgendes:
%                                   L3_A ≠ L3_B .
%             - 11.4.2: Vermeidung von Interferenz im L2-Cache:
%                       - 11.4.2.1: Falls L2 nicht CPU-gebunden ist: Analog zu 11.4.1.1.
%                       - 11.4.2.2: Falls L2 CPU-gebunden ist: Analog zu 11.4.1.2.
%     %- 11.1.6: Optimierung: Verteile möglichst alle Cache-Farben.
%     %        Priorisiere in absteigender Reihenfolge L3-Farben, L2-Farben, L1-Farben.
%     %- 11.1.7: TODO: Performanz-Constraints
%     %- 11.1.8: Minimiere der Anzahl der PageColors für Channel.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%  1. Eine endliche Menge von benannten Subjects, Kernels und Channels für die gilt:
% Als Fakten gegeben.

% TODO: Ggf. ein Constraint hinzufügen, um zu verhindern, dass ein X für mehrere MemoryRegion-Arten definiert wird.

%     - 1.1: Subjects und Kernels sind Executors.
executor(K) :- kernel(K).
executor(S) :- subject(S).

%     - 1.2: Subjects, Kernels und Channels sind MemoryRegions.
memory_region(K) :- kernel(K).
memory_region(S) :- subject(S).
memory_region(C) :- channel(C).

%     - 1.3: Ein Channel besitzt genau ein Executor, der zum Channel schreiben kann (Writer).
:- channel(C), not writes_to(executor(EX), channel(C)): executor(EX).
:- channel(C), 2 { writes_to(executor(EX), channel(C)): executor(EX) }.

%     - 1.4: Ein Channel besitzt ein oder mehrere Executors, die vom Channel lesen können (Readers).
:- channel(C), not reads_from(executor(EX), channel(C)): executor(EX).

%  2. Eine endliche Menge von N CPUs : CPUS = cpu(1..N).
% Als Fakten gegeben.

%  3. Das zweistellige Prädikat
%     ex_cpu(executor(X), cpu(Y)) : (Executors, CPUS) -> Bool, für das gilt:
% Als Fakten gegeben.

%     - 3.1: Jedem Executor X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen.
:- executor(EX), not ex_cpu(executor(EX), cpu(CPU)) : cpu(CPU).

%     - 3.2: Jeder CPU muss mindestens ein Executor zugeordnet worden sein.
:- cpu(CPU), not ex_cpu(executor(EX), cpu(CPU)) : executor(EX).

%     - 3.3: Aus 3.1 und 3.2 wird das zweistellige Prädikat
%             mr_cpu(memory_region(X), cpu(Y)) : (MemoryRegions, CPUS) -> Bool abgeleitet, für das gilt:

%             - 3.3.1: Executor-CPU entspricht der MemoryRegion-CPU:
mr_cpu(memory_region(EX), cpu(CPU)) :- ex_cpu(executor(EX), cpu(CPU)).

%             - 3.3.2: Zuordnung der CPUs des Writer oder des/der Reader(s) eines Channels zur MemoryRegion des
%                       Channels.

%                      - 3.3.2.1: Für Writer: Wenn writes_to(executor(EX), Channel(C)) und
%                                 ex_cpu(executor(EX), cpu(CPU)), dann: mr_cpu(memory_region(C), cpu(CPU)).
mr_cpu(memory_region(C), cpu(CPU)) :- channel(C), reads_from(executor(EX), channel(C)), ex_cpu(executor(EX), cpu(CPU)).

%                      - 3.3.2.2: Für Reader(s): Wenn reads_from(executor(EX), Channel(C)) und
%                                 ex_cpu(executor(EX), cpu(CPU)), dann: mr_cpu(memory_region(C), cpu(CPU).
mr_cpu(memory_region(C), cpu(CPU)) :- channel(C), writes_to(executor(EX), channel(C)), ex_cpu(executor(EX), cpu(CPU)).

%             - 3.3.3: Jedem MemoryRegion X wird ein oder mehrere CPUs ∈ 𝒫 ⁺(CPUS) zugewiesen. D. h. es gibt keine
%                      MemoryRegion, der keine CPU zugeordnet wurde.
:- memory_region(MR), not mr_cpu(memory_region(MR), cpu(CPU)) : cpu(CPU).

%             - 3.3.4: Jeder CPU muss mindestens ein MemoryRegion zugeordnet worden sein. ANNAHME: D. h. wir nehmen an,
%                      dass jede CPU benutzt wird.
:- cpu(CPU), not mr_cpu(memory_region(MR), cpu(CPU)) : memory_region(MR).

%  4. Das zweistellige Prädikat
%     mr_min_page_colors(memory_region(X), I) : (MemoryRegions, Positives) -> Bool, für das gilt:
% Als Fakten gegeben.

%     - 4.1: Für jede MemoryRegion wird die Mindest-Anzahl der zu verteilenden PageColors an diese MemoryRegion
%            spezifiziert. D. h. es gibt keine MemoryRegion für die keine Mindest-Anzahl definiert wurde.
%            ANNAHME: I > 0 (Wir wollen immer mindestens eine PageColor verteilen können).

%positive(I) :- I > 0.
%:- memory_region(MR),  not mr_min_page_colors(memory_region(MR), I) : positive(I).

%  5. Eine endliche Menge von N Cache-Levels : Levels = level(1..N).
% Als Fakten gegeben.

%  6. Das zweistellige Prädikat
%     cache_is_cpu_bound(level(X), Y). : (Levels, {yes, no}) -> Bool, für das gilt:
% Als Fakten gegeben.

%     - 6.1: Für jedes Level des Caches (üblicherweise drei Level) wird spezifiziert, ob die Caches dieses Levels an
%            eine CPU gebunden sind oder nicht. ANNAHME: Wird nehmen hier an, dass ein Cache entweder an genau eine
%            CPU gebunden ist oder nicht. D. h. ein Cache, der an zwei CPUs gebunden ist, kann noch nicht modelliert
%            werden.
% Als Fakten gegeben.

%  7. Eine endliche Menge von CacheColors pro Level (wir gehen hier von 3 Level aus).
% Als Fakten gegeben.

%  8. Eine endliche Menge von PageColors.
% Als Fakten gegeben.

%  9. Eine endliche Menge von N Cache-Isolationsdomänen : CacheIsolationDomains = cache_isolation_domain(1..N).
% Als Fakten gegeben.

% 10. Das zweistellige Prädikat
%     mr_cache_isolation(memory_region(X), cache_isolation_domain(Y)) : (MemoryRegions, CacheIsolationsDomains) -> Bool,
%     für das gilt:
% Als Fakten gegeben.

%     - 10.1: Jedem MemoryRegion X wird genau eine CacheIsolationDomain Y zugeordnet.
:- memory_region(MR), not 1 {mr_cache_isolation(memory_region(MR), cache_isolation_domain(CI)): cache_isolation_domain(CI)} 1.

%     - 10.2: Jeder CacheIsolationDomain wurde mindestens eine MemoryRegion zugeordnet.
:- cache_isolation_domain(CI), 0 {mr_cache_isolation(memory_region(MR), cache_isolation_domain(CI)): memory_region(MR)} 0.

% 11. Aus den Anforderungen von 1. bis einschließlich 10. werden zwei Prädikate abgeleitet, zum einen das Prädikat:
%     mr_pc(memory_region(X), page_color(...)) : (MemoryRegion, PageColors) -> Bool, das MemoryRegions die PageColors
%       verteilt, und zum anderen das Prädikat:
%     mr_spc(memory_region(X), system_page_color(cpu(CPU), page_color(...))) : (MemoryRegion, SystemPageColors) -> Bool,
%       das MemoryRegions die SystemPageColors verteilt, d. h. auch die CPUs mitbetrachten, die beim Zugriff auf die
%       MemoryRegions verwendet werden.
%     Für die Prädikate gelten:

%     - 11.1: Jeder MemoryRegion X werden mindestens so viel PageColors zugewiesen, wie durch
%             mr_min_page_colors(memory_region(X), I) spezifiziert wird.
1 { mr_pc(memory_region(MR), page_color(L1, L2, L3)) : page_color(L1, L2, L3)} :- memory_region(MR).

%     - 11.2: Beachtung aller CPUs einer MemoryRegions:
%             Wenn MemoryRegion X, den CPUs X_CPUS ∈ 𝒫 ⁺(CPUS) und den PageColors P1, P2, P3, ... zugeordnet wurde,
%             dann ordne X für jede CPU von X X_CPU ∈ X_CPUS die SystemPageColors
%             system_page_color(cpu(X_CPU), P1), system_page_color(cpu(X_CPU), P2),
%             system_page_color(cpu(X_CPU), P3), ... zu.
mr_spc(memory_region(MR), system_page_color(cpu(CPU), page_color(L1, L2, L3)))
    :- mr_pc(memory_region(MR), page_color(L1, L2, L3)), mr_cpu(memory_region(MR), cpu(CPU)).

%     - 11.4: Vermeidung von Interferenz im Cache:
%             Die Vermeidung von Interferenz im Cache ist abhängig davon, ob der Cache CPU-gebunden ist oder nicht.
%             Ist der Cache CPU-gebunden, dann muss die Verteilung der SystemPageColors betrachtet werden, ist der Cache
%             nicht CPU-gebunden, dann muss die Verteilung der PageColors betrachtet werden.

%             - 11.4.1: Vermeidung von Interferenz im L3-Cache:

%                       - 11.4.1.1: Falls L3 nicht CPU-gebunden ist:
%                                   Wenn MemoryRegion A und MemoryRegion B (und A!=B) sich in unterschiedlichen Cache-
%                                   Isolationsdomänen befinden, dann gilt paarweise für jede
%                                   PageColor-Zuordnung von A
%                                   mr_pc(A, page_color(cache_color(level(1), L1), cache_color(level(2), L2),
%                                     cache_color(level(3), L3_A)),
%                                   und für jede PageColor-Zuordnung von B
%                                   mr_pc(memory_region(B), page_color(cache_color(level(1), L1),
%                                     cache_color(level(2), L2), cache_color(level(3), L3_B))
%                                   folgendes:
%                                   L3_A ≠ L3_B .
MR1_L3 != MR2_L3 :-
    mr_cache_isolation(memory_region(MR1), cache_isolation_domain(CI1)),
    mr_cache_isolation(memory_region(MR2), cache_isolation_domain(CI2)),
    MR1 != MR2,
    CI1 != CI2,
    mr_pc(memory_region(MR1), page_color(_, _, MR1_L3)),
    mr_pc(memory_region(MR2), page_color(_, _, MR2_L3)),
    cache_is_cpu_bound(level(3), no).

%                       - 11.4.1.2: Falls L3 CPU-gebunden ist:
%                                   Wenn MemoryRegion A und MemoryRegion B (und A!=B) sich in unterschiedlichen Cache-
%                                   Isolationsdomänen befinden, dann gilt paarweise für jede
%                                   SystemPageColor-Zuordnung von A
%                                   mr_spc(memory_region(A), system_page_color(cpu(CPU_A),
%                                     page_color(cache_color(level(1), L1), cache_color(level(2), L2),
%                                     cache_color(level(3), L3_A))),
%                                   und für jede PageColor-Zuordnung von B
%                                   mr_spc(memory_region(B), system_page_color(cpu(CPU_B),
%                                     page_color(cache_color(level(1), L1), cache_color(level(2), L2),
%                                     cache_color(level(3), L3_B))),
%                                   folgendes:
%                                   L3_A ≠ L3_B .
MR1_L3 != MR2_L3 :-
    mr_cache_isolation(memory_region(MR1), cache_isolation_domain(CI1)),
    mr_cache_isolation(memory_region(MR2), cache_isolation_domain(CI2)),
    MR1 != MR2,
    CI1 != CI2,
    mr_spc(memory_region(MR1), system_page_color(cpu(CPU1), page_color(MR1_L1, MR1_L2, MR1_L3))),
    mr_spc(memory_region(MR2), system_page_color(cpu(CPU2), page_color(MR2_L1, MR2_L2, MR2_L3))),
    cache_is_cpu_bound(level(3), yes),
    CPU1 = CPU2.

%             - 11.4.2: Vermeidung von Interferenz im L2-Cache:

%                       - 11.4.2.1: Falls L2 nicht CPU-gebunden ist: Analog zu 11.4.1.1.
MR1_L2 != MR2_L2 :-
    mr_cache_isolation(memory_region(MR1), cache_isolation_domain(CI1)),
    mr_cache_isolation(memory_region(MR2), cache_isolation_domain(CI2)),
    MR1 != MR2,
    CI1 != CI2,
    mr_pc(memory_region(MR1), page_color(_, MR1_L2, _)),
    mr_pc(memory_region(MR2), page_color(_, MR2_L2, _)),
    cache_is_cpu_bound(level(2), no).

%                       - 11.4.2.2: Falls L2 CPU-gebunden ist: Analog zu 11.4.1.2.
MR1_L2 != MR2_L2 :-
    mr_cache_isolation(memory_region(MR1), cache_isolation_domain(CI1)),
    mr_cache_isolation(memory_region(MR2), cache_isolation_domain(CI2)),
    MR1 != MR2,
    CI1 != CI2,
    mr_spc(memory_region(MR1), system_page_color(cpu(CPU1), page_color(_, MR1_L2, _))),
    mr_spc(memory_region(MR2), system_page_color(cpu(CPU2), page_color(_, MR2_L2, _))),
    cache_is_cpu_bound(level(2), yes),
    CPU1 = CPU2.

%     %- 11.1.6: Optimierung: Verteile möglichst alle Cache-Farben.
%     %        Priorisiere in absteigender Reihenfolge L3-Farben, L2-Farben, L1-Farben.
#maximize { 16, cache_color(level(3), X) : mr_pc(_, page_color(_, _, cache_color(level(3), X))) }.
#maximize {  8, cache_color(level(2), X) : mr_pc(_, page_color(_, cache_color(level(2), X), _)) }.
#maximize {  4, cache_color(level(1), X) : mr_pc(_, page_color(cache_color(level(1), X), _, _)) }.

% Für das Debugging: Ausgabe der Anzahl der verteilten Farben pro Cache-Level.
mapped(L1) :- mr_pc(_, page_color(L1, _, _)).
mapped(L2) :- mr_pc(_, page_color(_, L2, _)).
mapped(L3) :- mr_pc(_, page_color(_, _, L3)).

l3_count(N) :- #count {X : mapped(cache_color(level(3), X)) } = N.
l2_count(N) :- #count {X : mapped(cache_color(level(2), X)) } = N.
l1_count(N) :- #count {X : mapped(cache_color(level(1), X)) } = N.
