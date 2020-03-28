from math import ceil
from typing import Dict, Set, Union

from clorm import Predicate, ConstantField, IntegerField, FactBase, RawField, ComplexTerm
from clorm.clingo import Control, Function, Symbol
import itertools

import clorm.clingo
import page_coloring_model as PageColoringModel
from page_coloring_model_clingo_printer import PageColoringModelClingoPrinter

import logging

class Memory_region(Predicate):
    name = ConstantField


class Executor(Predicate):
    name = ConstantField


class Kernel(Predicate):
    name = ConstantField


class Subject(Predicate):
    name = ConstantField


class Channel(Predicate):
    name = ConstantField


class Reads_from(Predicate):
    executor = Executor.Field
    channel = Channel.Field


class Writes_to(Predicate):
    executor = Executor.Field
    channel = Channel.Field


class Cpu(Predicate):
    cpu_id = IntegerField


class Ex_cpu(Predicate):
    name = Executor.Field
    cpu = Cpu.Field


class Level(Predicate):
    level_id = IntegerField


class Cache_color(Predicate):
    level = Level.Field
    cache_id = IntegerField


class Page_color(Predicate):
    l1_cc = Cache_color.Field
    l2_cc = Cache_color.Field
    l3_cc = Cache_color.Field


class System_page_color(Predicate):
    cpu = Cpu.Field
    pc = Page_color.Field


class Cache_isolation_domain(Predicate):
    cid_id = IntegerField


class Mr_cache_isolation(Predicate):
    mr = Memory_region.Field
    cid = Cache_isolation_domain.Field


class Mr_pc(Predicate):
    mr = Memory_region.Field
    pc = Page_color.Field
# class Map_pc(Predicate):
#     memory_region = RawField
#     page_color = Page_color.Field


class Mr_spc(Predicate):
    mr = Memory_region.Field
    spc = System_page_color.Field


class L3_count(Predicate):
    num = IntegerField


class L2_count(Predicate):
    num = IntegerField


class L1_count(Predicate):
    num = IntegerField


class Mr_cpu(Predicate):
    mr = Memory_region.Field
    cpu = Cpu.Field


class Mapped(Predicate):
    cc = Cache_color.Field


class Mr_min_page_colors(Predicate):
    mr = Memory_region.Field
    minimum = IntegerField


class Cache_is_cpu_bound(Predicate):
    cache_level = Level.Field
    yes_no = ConstantField


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

        cname = PageColoringModelClingoPrinter.convert_to_clingo_name

        assignment = {system_page_color: set() for system_page_color in system.get_system_page_colors()}

        ASP_PROGRAM_PATH = "asp_programs/page-coloring.lp"

        memory_regions = system.get_memory_regions()

        # Create mapping from clingo predicate to MemoryRegion name
        predicate_to_memory_region = {}
        for memory_region in memory_regions:
            predicate_to_memory_region[Memory_region(name=cname(memory_region.get_name()))] = memory_region

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

        channel_names = [
            (cname(memory_region.get_name()))
            for memory_region in memory_regions
            if isinstance(memory_region, PageColoringModel.Channel)
        ]

        cpu_cores = system.get_hardware().get_cpu_cores()

        kernels = [Kernel(name=n) for n in kernel_names]
        subjects = [Subject(name=n) for n in subject_names]
        #channels = [Channel(source=Executor(name=src), target=Executor(name=trgt)) for (src, trgt) in channel_names]
        channels = [Channel(name=name) for name in channel_names]

        reads_from = []
        writes_to = []
        for memory_region in memory_regions:
            if isinstance(memory_region, PageColoringModel.Channel):
                mr_name = cname(memory_region.get_name())
                for reader in memory_region.get_readers():
                    reader_name = cname(reader.get_name())
                    reads_from.append(
                        Reads_from(executor=Executor(name=reader_name), channel=Channel(name=mr_name))
                    )
                writer_name = cname(memory_region.get_writer().get_name())
                writes_to.append(
                    Writes_to(executor=Executor(name=writer_name), channel=Channel(name=mr_name))
                )


        cpus = [Cpu(cpu_id=int(cpu_core.get_id())) for cpu_core in cpu_cores]

        ex_cpus = []
        for executor, cpu_list in executor_cpu_constraints.items():
            for cpu in cpu_list:
                executor_name = cname(executor.get_name())
                ex_cpus.append(
                    Ex_cpu(name=Executor(name=executor_name), cpu=Cpu(cpu_id=int(cpu.get_id())))
                    #Ex_cpu(name=executor_name, cpu_id=int(cpu.get_id()))
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
            #L1_color(cache_id=int(cache_id), cpu_id=int(cpu_core.get_id()))
            Cache_color(level=Level(level_id=1), cache_id=cache_id)
            for (cache_id, cpu_core)
            in itertools.product(l1_cache_ids, cpu_cores)
        ]

        l2_colors = [
            #L2_color(cache_id=int(cache_id), cpu_id=int(cpu_core.get_id()))
            Cache_color(level=Level(level_id=2), cache_id=cache_id)
            for (cache_id, cpu_core)
            in itertools.product(l2_cache_ids, cpu_cores)
        ]

        l3_colors = [
            #L3_color(cache_id=int(cache_id))
            Cache_color(level=Level(level_id=3), cache_id=cache_id)
            for cache_id in l3_cache_ids
        ]

        predicate_to_system_page_color = {}
        page_colors = []
        for system_page_color in system.get_system_page_colors():
            cpu_id = int(system_page_color.get_cpu().get_id())
            page_color = system_page_color.get_page_color()
            l1 = page_color.get_cache_colors()[0]
            l2 = page_color.get_cache_colors()[1]
            l3 = page_color.get_cache_colors()[2]
            l1_color = int(l1.get_id())
            l2_color = int(l2.get_id())
            l3_color = int(l3.get_id())

            page_color = Page_color(
                    l1_cc=Cache_color(level=Level(level_id=1), cache_id=l1_color),
                    l2_cc=Cache_color(level=Level(level_id=2), cache_id=l2_color),
                    l3_cc=Cache_color(level=Level(level_id=3), cache_id=l3_color)
                )
            predicate = System_page_color(
                cpu = Cpu(cpu_id=cpu_id),
                pc = page_color
            )
            page_colors.append(page_color)
            predicate_to_system_page_color[predicate] = system_page_color

        clingo_cache_isolations_domains = [
            Cache_isolation_domain(cid_id=i) for i in range(1, len(cache_isolation_domains) + 1)
        ]

        mr_cache_isolations = []
        for cid_id, cache_isolation_domain in enumerate(cache_isolation_domains, start=1):
            for member in cache_isolation_domain:
                mr_name = cname(member.get_name())

                mr_cache_isolations.append(
                    Mr_cache_isolation(
                        mr=Memory_region(name=mr_name),
                        cid=Cache_isolation_domain(cid_id=cid_id)
                    )
                )

        # Calculate minimum numbers of page colors of a MemoryRegion
        mr_min_page_colors = []
        num_of_page_colors = len(system.get_page_colors())
        pages_per_page_color = len(system.get_hardware().get_page_addresses()) / num_of_page_colors
        page_size = system.get_hardware().get_page_size()
        for memory_region in system.get_memory_regions():
            min_page_colors_of_mr = int(ceil(
                (memory_region.get_memory_size() / page_size) / pages_per_page_color
            ))
            #logging.debug("Minimum page colors of " + memory_region.get_name() + ": " + str(min_page_colors_of_mr))

            mr_name = cname(memory_region.get_name())

            mr_min_page_colors_pred = Mr_min_page_colors(
                mr=Memory_region(name=mr_name),
                minimum=min_page_colors_of_mr
            )

            mr_min_page_colors.append(mr_min_page_colors_pred)

        print(str(mr_min_page_colors))

        # TODO: Hardcoded
        cache_is_cpu_bound_properties = [
            Cache_is_cpu_bound(cache_level=Level(level_id=1), yes_no="yes"),
            Cache_is_cpu_bound(cache_level=Level(level_id=2), yes_no="yes"),
            Cache_is_cpu_bound(cache_level=Level(level_id=3), yes_no="no")
        ]

        ##

        ctrl = Control(
            unifier=[
                Memory_region, Executor,
                Kernel, Subject, Channel, Cpu, Ex_cpu,
                Cache_color, Page_color, System_page_color,
                Cache_isolation_domain,
                Mr_cache_isolation,
                Mr_pc,
                L3_count, L2_count, L1_count,
                Mr_cpu, Mapped, Mr_min_page_colors, Mr_spc,
                Cache_is_cpu_bound, Level,
                Reads_from, Writes_to
            ])
        ctrl.load(ASP_PROGRAM_PATH)

        fact_base = kernels + subjects + channels + cpus + ex_cpus + \
                    l1_colors + l2_colors + l3_colors + page_colors + \
                    clingo_cache_isolations_domains + \
                    mr_cache_isolations + mr_min_page_colors + cache_is_cpu_bound_properties + \
                    reads_from + writes_to

        instance = FactBase(fact_base)

        # Show fact base.
        print(instance.asp_str())

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

        logging.debug("hallo"+solution.asp_str())

        query1 = solution.select(L1_count)
        query2 = solution.select(L2_count)
        query3 = solution.select(L3_count)
        #query4 = solution.select(Map_pc).order_by(Map_pc.memory_region)
        query4 = solution.select(Mr_spc).order_by(Mr_spc.mr)

        l1_counts = query1.get()
        l2_counts = query2.get()
        l3_counts = query3.get()
        mapped_system_page_colors = query4.get()

        logging.info("Mapped L1 colors: " + str(l1_counts[0].num))
        logging.info("Mapped L2 colors: " + str(l2_counts[0].num))
        logging.info("Mapped L3 colors: " + str(l3_counts[0].num))

        for mapping in mapped_system_page_colors:
            memory_region = predicate_to_memory_region[
                Memory_region(name=mapping.mr.name)
            ]

            system_page_color = predicate_to_system_page_color[mapping.spc]
            assignment[system_page_color].add(memory_region)

        return assignment
