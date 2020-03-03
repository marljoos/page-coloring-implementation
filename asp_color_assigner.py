from typing import Dict, Set

from clorm import Predicate, ConstantField, IntegerField, ph1_, FactBase, RawField, ComplexTerm,\
            simple_predicate
from clorm.clingo import Control, Function, Symbol, String
import itertools

import clorm.clingo
# TODO: Circular dependency
from page_coloring_model import ClingoPrinter, System
import page_coloring_model as PageColoringModel


class Memory_consumer(Predicate):
    name = RawField


#CMemory_consumer_alt = simple_predicate("cmemory_consumer", 1)
# Success

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


class Mc_cache_isolation(Predicate):
    member = RawField
    cid_id = IntegerField


class Map_pc(Predicate):
    memory_consumer = RawField
    page_color = Page_color.Field


class L3_count(Predicate):
    num = IntegerField


class L2_count(Predicate):
    num = IntegerField


class L1_count(Predicate):
    num = IntegerField


class Mc_cpu(Predicate):
    memory_consumer = RawField
    cpu_id = IntegerField


class Mapped(Predicate):
    color = RawField


class ASPColorAssigner:
    @staticmethod
    def get_assignment_by_cache_isolation_domain_method(
            system: PageColoringModel.System,
            cache_isolation_domains,
            executor_cpu_constraints
    ) -> Dict[PageColoringModel.Hardware.SystemPageColorNew, Set[PageColoringModel.MemoryConsumer]]:

        #assignment: Dict[PageColoringModel.Hardware.SystemPageColorNew, Set[PageColoringModel.MemoryConsumer]] = {}
        assignment = {system_page_color: set() for system_page_color in system.get_system_page_colors()}

        # for spc in assignment.keys():
        #     print("test:" + str(spc))

        ASP_PROGRAM_PATH = "asp_programs/page-coloring.pl"
        cname = ClingoPrinter.convert_to_clingo_name

        all_memory_consumers = system.get_all_memory_consumers()

        # Create mapping from clingo name to MemoryConsumer name
        predicate_to_memory_consumer = {}
        for memory_consumer in all_memory_consumers:
            if isinstance(memory_consumer, PageColoringModel.Kernel):
                predicate_to_memory_consumer[Memory_consumer(name=cname(memory_consumer.get_name()))] = memory_consumer
            elif isinstance(memory_consumer, PageColoringModel.Subject):
                predicate_to_memory_consumer[Memory_consumer(name=cname(memory_consumer.get_name()))] = memory_consumer
            elif isinstance(memory_consumer, (PageColoringModel.Channel)):
                src = cname(memory_consumer.get_source().get_name())
                trgt = cname(memory_consumer.get_target().get_name())
                predicate_to_memory_consumer[Channel(source=src, target=trgt)] = memory_consumer
            else:
                assert False, "Unexpected condition. Unknown MemoryConsumer class."

        all_kernel_names = [
            cname(memory_consumer.get_name())
            for memory_consumer in all_memory_consumers
            if isinstance(memory_consumer, PageColoringModel.Kernel)
        ]

        all_subject_names = [
            cname(memory_consumer.get_name())
            for memory_consumer in all_memory_consumers
            if isinstance(memory_consumer, PageColoringModel.Subject)
        ]

        # channel name does mean (source_name, target_name) here
        all_channel_names = [
            (cname(memory_consumer.get_source().get_name()),
             cname(memory_consumer.get_target().get_name()))
            for memory_consumer in all_memory_consumers
            if isinstance(memory_consumer, PageColoringModel.Channel)
        ]

        cpu_cores = system.get_hardware().get_cpu_cores()

        kernels = [Kernel(name=n) for n in all_kernel_names]
        subjects = [Subject(name=n) for n in all_subject_names]
        channels = [Channel(source=src, target=trgt) for (src, trgt) in all_channel_names]
        cpus = [Cpu(cpu_id=int(cpu_core.get_name_without_prefix())) for cpu_core in cpu_cores]

        ex_cpus = []
        for executor, cpu_list in executor_cpu_constraints.items():
            for cpu in cpu_list:
                executor_name = cname(executor.get_name())
                ex_cpus.append(
                    Ex_cpu(name=executor_name, cpu_id=int(cpu.get_name_without_prefix()))
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
            L1_color(cache_id=int(cache_id), cpu_id=int(cpu_core.get_name_without_prefix()))
            for (cache_id, cpu_core)
            in itertools.product(l1_cache_ids, cpu_cores)
        ]

        l2_colors = [
            L2_color(cache_id=int(cache_id), cpu_id=int(cpu_core.get_name_without_prefix()))
            for (cache_id, cpu_core)
            in itertools.product(l2_cache_ids, cpu_cores)
        ]

        l3_colors = [L3_color(cache_id=int(cache_id)) for cache_id in l3_cache_ids]

        # page_colors = []
        # for page_color in system.get_page_colors():
        #     l1 = page_color.get_cache_colors()[0]
        #     l2 = page_color.get_cache_colors()[1]
        #     l3 = page_color.get_cache_colors()[2]
        #     l1_color = l1.get_name_without_prefix()
        #     l2_color = l2.get_name_without_prefix()
        #     l3_color = l3.get_name_without_prefix()
        #     for cpu in cpu_cores:
        #         cpu_id = int(cpu.get_name_without_prefix())
        #
        #         page_colors.append(
        #             Page_color(
        #                 l1_color=L1_color(cache_id=int(l1_color), cpu_id=cpu_id),
        #                 l2_color=L2_color(cache_id=int(l2_color), cpu_id=cpu_id),
        #                 l3_color=L3_color(cache_id=int(l3_color))
        #             )
        #         )

        predicate_to_system_page_color = {}
        page_colors = []
        for system_page_color in system.get_system_page_colors():
            cpu_id = int(system_page_color.get_cpu().get_name_without_prefix())
            page_color = system_page_color.get_page_color()
            l1 = page_color.get_cache_colors()[0]
            l2 = page_color.get_cache_colors()[1]
            l3 = page_color.get_cache_colors()[2]
            l1_color = l1.get_name_without_prefix()
            l2_color = l2.get_name_without_prefix()
            l3_color = l3.get_name_without_prefix()

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

        mc_cache_isolations = []
        for cid_id, cache_isolation_domain in enumerate(cache_isolation_domains, start=1):
            for member in cache_isolation_domain:
                if not isinstance(member, PageColoringModel.Channel):
                    memory_consumer = cname(member.get_name())
                    mc_cache_isolations.append(
                        # CMc_cache_isolation(member=CMemory_consumer(name=Function(memory_consumer)), cid_id=cid_id)
                        Mc_cache_isolation(member=clorm.clingo.Function(memory_consumer), cid_id=cid_id)
                    )
                elif isinstance(member, PageColoringModel.Channel):
                    source_name = cname(member.get_source().get_name())
                    target_name = cname(member.get_target().get_name())
                    mc_name = "c(" + source_name + "," + target_name + ")"
                    # CMemory_consumer_alt
                    mc_cache_isolations.append(
                        Mc_cache_isolation(
                            # member=CMemory_consumer(name=Function("c", [Function(source_name), Function(target_name)])),
                            # cid_id=int(cid_id)
                            member=Function("c", [Function(source_name), Function(target_name)]),
                            cid_id=int(cid_id)
                        )
                        # CMc_cache_isolation(member=C(source=source_name, target=target_name), cid_id=cid_id)
                    )
                else:
                    assert False, "Unexpected condition."

        #######################

        ctrl = Control(
            unifier=[
                Memory_consumer, Executor,
                Kernel, Subject, Channel, Cpu, Ex_cpu,
                L1_color, L2_color, L3_color, Page_color,
                Cache_isolation_domain,
                Mc_cache_isolation,
                Map_pc,
                L3_count, L2_count, L1_count,
                Mc_cpu, Mapped  # , C
            ])
        ctrl.load(ASP_PROGRAM_PATH)

        fact_base = kernels + subjects + channels + cpus + ex_cpus + \
                    l1_colors + l2_colors + l3_colors + page_colors + \
                    clingo_cache_isolations_domains + \
                    mc_cache_isolations

        instance = FactBase(fact_base)

        # print(instance.asp_str())

        ctrl.add_facts(instance)
        ctrl.ground([("base", [])])
        solution = None

        def on_model(model):
            nonlocal solution
            solution = model.facts(atoms=True)

        ctrl.solve(on_model=on_model)
        if not solution:
            raise ValueError("No solution found")

        query1 = solution.select(L1_count)
        query2 = solution.select(L2_count)
        query3 = solution.select(L3_count)
        query4 = solution.select(Map_pc).order_by(Map_pc.memory_consumer)
        query5 = solution.select(Memory_consumer)
        query6 = solution.select(Channel)
        query7 = solution.select(Executor)

        l1_counts = query1.get()
        l2_counts = query2.get()
        l3_counts = query3.get()
        mapped_page_colors = query4.get()
        memory_consumers = query5.get()
        asp_channels = query6.get()
        asp_executors = query7.get()

        print("Mapped L1 colors: " + str(l1_counts[0].num))
        print("Mapped L2 colors: " + str(l2_counts[0].num))
        print("Mapped L3 colors: " + str(l3_counts[0].num))

        for mapping in mapped_page_colors:
            #print(str(mapping.memory_consumer) + " -> " + str(mapping.page_color))
            #print("Test:" + str(type(mapping.memory_consumer)) + str(type(mapping.page_color)))
            if isinstance(mapping.memory_consumer, Memory_consumer):
                assert False, "Unexpected."
                # mapping.memory_consumer = predicate_to_memory_consumer[mapping.memory_consumer]
            elif isinstance(mapping.memory_consumer, Symbol):
                if mapping.memory_consumer.name == "c":  # Channel
                    assert len(mapping.memory_consumer.arguments) == 2
                    src = str(mapping.memory_consumer.arguments[0])
                    trgt = str(mapping.memory_consumer.arguments[1])
                    memory_consumer =\
                        predicate_to_memory_consumer[Channel(source=src, target=trgt)]
                elif len(mapping.memory_consumer.arguments) == 0:
                    memory_consumer = \
                        predicate_to_memory_consumer[Memory_consumer(name=mapping.memory_consumer.name)]
                else:
                    # print(str(mapping.memory_consumer.name))
                    assert False, "Unexpected."
            else:
                assert False, "Unexpected."

            #print(str(type(mapping.page_color)))
            system_page_color = predicate_to_system_page_color[mapping.page_color]
            #print(str(system_page_color))
            assignment[system_page_color].add(memory_consumer)

        # for mc in memory_consumers:
        #     print(str(mc))
        #     print(type(mc))
        #
        # for c in asp_channels:
        #     print(str(c))
        #
        # for e in asp_executors:
        #     print(str(e))

        return assignment