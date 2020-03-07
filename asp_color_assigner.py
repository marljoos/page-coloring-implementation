from typing import Dict, Set

from clorm import Predicate, ConstantField, IntegerField, FactBase, RawField
from clorm.clingo import Control, Function, Symbol
import itertools

import clorm.clingo
import page_coloring_model as PageColoringModel
from page_coloring_model_clingo_printer import PageColoringModelClingoPrinter

import logging


class Memory_region(Predicate):
    name = RawField


class Executor(Predicate):
    name = ConstantField


class Kernel(Predicate):
    name = ConstantField


class Subject(Predicate):
    name = ConstantField


class Channel(Predicate):
    source = ConstantField
    target = ConstantField


class Cpu(Predicate):
    cpu_id = IntegerField


class Ex_cpu(Predicate):
    name = ConstantField
    cpu_id = IntegerField


class L1_color(Predicate):
    cache_id = IntegerField
    cpu_id = IntegerField


class L2_color(Predicate):
    cache_id = IntegerField
    cpu_id = IntegerField


class L3_color(Predicate):
    cache_id = IntegerField


class Page_color(Predicate):
    l1_color = L1_color.Field
    l2_color = L2_color.Field
    l3_color = L3_color.Field


class Cache_isolation_domain(Predicate):
    cid_id = IntegerField


class Mr_cache_isolation(Predicate):
    member = RawField
    cid_id = IntegerField


class Map_pc(Predicate):
    memory_region = RawField
    page_color = Page_color.Field


class L3_count(Predicate):
    num = IntegerField


class L2_count(Predicate):
    num = IntegerField


class L1_count(Predicate):
    num = IntegerField


class Mr_cpu(Predicate):
    memory_region = RawField
    cpu_id = IntegerField


class Mapped(Predicate):
    color = RawField


class ASPColorAssigner(PageColoringModel.ColorAssigner):
    @staticmethod
    def get_assignment(
            system: PageColoringModel.System,
            cache_isolation_domains,
            executor_cpu_constraints
    ) -> Dict[PageColoringModel.Hardware.SystemPageColor, Set[PageColoringModel.MemoryRegion]]:
        """Assign colors by cache isolation domains method.

        A cache isolation domain contains a set of memory regions and separates them (in the sense of cache
        non-interference) from other memory regions of the system. Therefore memory regions of the same
        cache isolation domain reserve a set of colors which can be used by them and cannot be used by memory regions
        which are not member of the same cache isolation domain.

        The set of colors assigned to an Executor can be further constrained by Executor-CPU-constraints.
        Executor-CPU-constraints constraints the set of reservable colors of an Executors to the set of colors of
        certain specified CPUs.
        E. g.: On a 4-core systems, a subject X can be constrained to only reserve colors of
        the kind (CPU_0, $num_colors), (CPU_3, $num_colors), which implicitly disallows all colors of the classes
        (CPU_1, $num_colors) and (CPU_2, $num_colors), such as (CPU_1, 0), (CPU_1, 1), (CPU_2, 0), (CPU_2, 1), ...
        An Executor-CPU-constraint does not mean that an executor gets a CPU core exclusively. Thus other Executors may
        also reserve colors which are using the same CPU core.
        Executor-CPU-constraints can especially be used for finding valid colors assignments of existing scheduling
        plans which have already assigned CPU cores to executors.
        The current implementation requires that all Executors of the system are assigned to at least on CPU core.
        #ASSMS-CACHE-ISOLATION-6

        CPU-Access-Constraints are currently unimplemented/not needed.
        #Besides Executor-CPU-constraints the assignment of colors can also be further constrained by
        #CPU-Access-Constraints. A CPU-Access-Constraint specifies a set of Executors which exclusively own a CPU core
        #and thus only the specified Executors may reserve a System Page Color of the CPU.
        #E. g.: if "CPU_0 -> {subject_X, subject_Y}" is specified as one CPU-Access-Constraint, then only subject_X and
        #subject_Y (and no other Executors) are allowed to reserve System Page Colors of the form
        #(CPU_0, 0), (CPU_0, 1), ... . Other CPU-Access-Constraints may additionally expand the space of reservable
        #System Page Colors of subject_X and/or subject_Y independently (e. g. "CPU_1" -> {subject_X},
        #"CPU_2" -> {subject_Y, subject_Z}).
        #CPU-Access-Constraints can especially be used to enforce stricter isolation between Executors to prevent
        #further shared microarchitectural state besides caches.

        Assumptions and preconditions:
            - All memory regions of the system must be assigned at least to one cache isolation domain.
              #ASSMS-CACHE-ISOLATION-0
            - A memory region can only be member of one cache isolation domain. #ASSMS-CACHE-ISOLATION-1
            # For simplicity commented out for now:
            #- If the cache isolation domain of a memory region is not explicitly specified by
            #  cache_isolation_domains,
            #  it is implicitly assumed that the memory region gets its own exclusive cache isolation domain.
            #  #ASSMS-CACHE-ISOLATION-2
            - The specification of the constraints could have inconsistencies such as "subject_X -> CPU_0" as an
              Executor-CPU-Constraint and "CPU_0 -> {subject_A, subject_B}" as a CPU-Access-Constraint.
              There must be no inconsistencies between Executor-CPU-Constraints and CPU-Access-Constraints.
              #ASSMS-CACHE-ISOLATION-3
            - An Executor contained in any constraint must be an executor of the hardware system provided.
              #ASSMS-CACHE-ISOLATION-4
            - A CPU core contained in any constraint must be a CPU core of the hardware system provided.
              #ASSMS-CACHE-ISOLATION-5
            - The current implementation requires that all Executors of the system are assigned to at least on CPU core.
              #ASSMS-CACHE-ISOLATION-6
            - CPU-Access-Constraints are currently unimplemented/not needed. #ASSMS-CACHE-ISOLATION-7

        Args:
            system: The system (consists of hardware and memory regions).
            cache_isolation_domains: Cache isolation domains for which a valid page coloring is requested.
            executor_cpu_constraints: Executor-CPU-Constraints which must enforced on top of the cache isolation
                domains. See function documentation for details.
            cpu_access_constraints: (Currently not implemented/not needed) CPU-Access-Constraints which must enforced on
                top of the cache isolation domains. See function documentation for details.
        """

        assignment = {system_page_color: set() for system_page_color in system.get_system_page_colors()}

        ASP_PROGRAM_PATH = "asp_programs/page-coloring.pl"

        cname = PageColoringModelClingoPrinter.convert_to_clingo_name

        memory_regions = system.get_memory_regions()

        # Create mapping from clingo name to MemoryRegion name
        predicate_to_memory_region = {}
        for memory_region in memory_regions:
            if isinstance(memory_region, PageColoringModel.Kernel):
                predicate_to_memory_region[Memory_region(name=cname(memory_region.get_name()))] = memory_region
            elif isinstance(memory_region, PageColoringModel.Subject):
                predicate_to_memory_region[Memory_region(name=cname(memory_region.get_name()))] = memory_region
            elif isinstance(memory_region, (PageColoringModel.Channel)):
                src = cname(memory_region.get_source().get_name())
                trgt = cname(memory_region.get_target().get_name())
                predicate_to_memory_region[Channel(source=src, target=trgt)] = memory_region
            else:
                assert False, "Unexpected condition. Unknown MemoryRegion class."

        kernel_names = [
            cname(memory_region.get_name())
            for memory_region in memory_regions
            if isinstance(memory_region, PageColoringModel.Kernel)
        ]

        subject_names = [
            cname(memory_region.get_name())
            for memory_region in memory_regions
            if isinstance(memory_region, PageColoringModel.Subject)
        ]

        # channel name does mean (source_name, target_name) here
        channel_names = [
            (cname(memory_region.get_source().get_name()),
             cname(memory_region.get_target().get_name()))
            for memory_region in memory_regions
            if isinstance(memory_region, PageColoringModel.Channel)
        ]

        cpu_cores = system.get_hardware().get_cpu_cores()

        kernels = [Kernel(name=n) for n in kernel_names]
        subjects = [Subject(name=n) for n in subject_names]
        channels = [Channel(source=src, target=trgt) for (src, trgt) in channel_names]
        cpus = [Cpu(cpu_id=int(cpu_core.get_id())) for cpu_core in cpu_cores]

        ex_cpus = []
        for executor, cpu_list in executor_cpu_constraints.items():
            for cpu in cpu_list:
                executor_name = cname(executor.get_name())
                ex_cpus.append(
                    Ex_cpu(name=executor_name, cpu_id=int(cpu.get_id()))
                )

        # TODO: Everything CacheColors related is inflexible. To be refactored.
        cache_information = system.get_hardware().get_cache_information()
        num_l1_colors = cache_information[0].get_number_of_colors()  # TODO: Hardcoded
        num_l2_colors = cache_information[1].get_number_of_colors()  # TODO: Hardcoded
        num_l3_colors = cache_information[2].get_number_of_colors()  # TODO: Hardcoded

        l1_cache_ids = list(range(1, num_l1_colors + 1))
        l2_cache_ids = list(range(1, num_l2_colors + 1))
        l3_cache_ids = list(range(1, num_l3_colors + 1))

        l1_colors = [
            L1_color(cache_id=int(cache_id), cpu_id=int(cpu_core.get_id()))
            for (cache_id, cpu_core)
            in itertools.product(l1_cache_ids, cpu_cores)
        ]

        l2_colors = [
            L2_color(cache_id=int(cache_id), cpu_id=int(cpu_core.get_id()))
            for (cache_id, cpu_core)
            in itertools.product(l2_cache_ids, cpu_cores)
        ]

        l3_colors = [L3_color(cache_id=int(cache_id)) for cache_id in l3_cache_ids]

        predicate_to_system_page_color = {}
        page_colors = []
        for system_page_color in system.get_system_page_colors():
            cpu_id = int(system_page_color.get_cpu().get_id())
            page_color = system_page_color.get_page_color()
            l1 = page_color.get_cache_colors()[0]
            l2 = page_color.get_cache_colors()[1]
            l3 = page_color.get_cache_colors()[2]
            l1_color = l1.get_id()
            l2_color = l2.get_id()
            l3_color = l3.get_id()

            predicate = Page_color(
                    l1_color=L1_color(cache_id=int(l1_color), cpu_id=cpu_id),
                    l2_color=L2_color(cache_id=int(l2_color), cpu_id=cpu_id),
                    l3_color=L3_color(cache_id=int(l3_color))
            )
            page_colors.append(predicate)
            predicate_to_system_page_color[predicate] = system_page_color

        clingo_cache_isolations_domains = [
            Cache_isolation_domain(cid_id=i) for i in range(1, len(cache_isolation_domains) + 1)
        ]

        mr_cache_isolations = []
        for cid_id, cache_isolation_domain in enumerate(cache_isolation_domains, start=1):
            for member in cache_isolation_domain:
                if not isinstance(member, PageColoringModel.Channel):
                    memory_region = cname(member.get_name())

                    mr_cache_isolations.append(
                        Mr_cache_isolation(member=clorm.clingo.Function(memory_region), cid_id=cid_id)
                    )
                elif isinstance(member, PageColoringModel.Channel):
                    source_name = cname(member.get_source().get_name())
                    target_name = cname(member.get_target().get_name())

                    mr_cache_isolations.append(
                        Mr_cache_isolation(
                            member=Function("c", [Function(source_name), Function(target_name)]),
                            cid_id=int(cid_id)
                        )
                    )
                else:
                    assert False, "Unexpected condition."

        ##

        ctrl = Control(
            unifier=[
                Memory_region, Executor,
                Kernel, Subject, Channel, Cpu, Ex_cpu,
                L1_color, L2_color, L3_color, Page_color,
                Cache_isolation_domain,
                Mr_cache_isolation,
                Map_pc,
                L3_count, L2_count, L1_count,
                Mr_cpu, Mapped  # , C
            ])
        ctrl.load(ASP_PROGRAM_PATH)

        fact_base = kernels + subjects + channels + cpus + ex_cpus + \
                    l1_colors + l2_colors + l3_colors + page_colors + \
                    clingo_cache_isolations_domains + \
                    mr_cache_isolations

        instance = FactBase(fact_base)

        # Show fact base.
        # print(instance.asp_str())

        ctrl.add_facts(instance)
        ctrl.ground([("base", [])])
        solution = None

        def on_model(model):
            nonlocal solution
            solution = model.facts(atoms=True)

        ctrl.solve(on_model=on_model)
        if not solution:
            raise ASPColorAssigner.ColorAssignmentException(
                "No ASP solution found. Error can be anything. ASP unsatisfiability is hard to debug."
            )

        query1 = solution.select(L1_count)
        query2 = solution.select(L2_count)
        query3 = solution.select(L3_count)
        query4 = solution.select(Map_pc).order_by(Map_pc.memory_region)

        l1_counts = query1.get()
        l2_counts = query2.get()
        l3_counts = query3.get()
        mapped_page_colors = query4.get()

        logging.info("Mapped L1 colors: " + str(l1_counts[0].num))
        logging.info("Mapped L2 colors: " + str(l2_counts[0].num))
        logging.info("Mapped L3 colors: " + str(l3_counts[0].num))

        for mapping in mapped_page_colors:
            if isinstance(mapping.memory_region, Symbol):
                if mapping.memory_region.name == "c":  # Channel
                    assert len(mapping.memory_region.arguments) == 2
                    src = str(mapping.memory_region.arguments[0])
                    trgt = str(mapping.memory_region.arguments[1])
                    memory_region =\
                        predicate_to_memory_region[Channel(source=src, target=trgt)]
                elif len(mapping.memory_region.arguments) == 0:
                    memory_region = \
                        predicate_to_memory_region[Memory_region(name=mapping.memory_region.name)]
                else:
                    assert False, "Unexpected."
            else:
                assert False, "Unexpected."

            system_page_color = predicate_to_system_page_color[mapping.page_color]
            assignment[system_page_color].add(memory_region)

        return assignment
