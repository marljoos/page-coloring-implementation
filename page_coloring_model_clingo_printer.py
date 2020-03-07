from page_coloring_model import *
from typing import Dict, Set, Union


class PageColoringModelClingoPrinter:

    @staticmethod
    def convert_to_clingo_name(name: str):
        """Clingo name (of instances and predicates) must be lowercase, without spaces and hyphens."""

        lower_case = name.lower()
        without_space = lower_case.replace(' ', '_')
        without_hyphen = without_space.replace('-', '_')

        return without_hyphen

    @staticmethod
    def print_executors(executors):
        clingo = PageColoringModelClingoPrinter.convert_to_clingo_name

        for executor in executors.values():
            class_name = type(executor).__name__
            executor_name = executor.get_name()

            print(clingo(class_name) + "(" + clingo(executor_name) + ").")

    @staticmethod
    def print_channels(channels):
        clingo = PageColoringModelClingoPrinter.convert_to_clingo_name

        for channel in channels:
            source_name = channel.get_source().get_name()
            target_name = channel.get_target().get_name()

            print("channel(" + clingo(source_name) + ", " + clingo(target_name) + ").")

    @staticmethod
    def print_cpus(cpu_cores):
        print("cpu(1.." + str(len(cpu_cores)) + ").")

    @staticmethod
    def print_executor_cpu_constraints(executor_cpu_constraints : Dict[Union[Kernel, Subject], Set[Hardware.CPU]]):
        clingo = PageColoringModelClingoPrinter.convert_to_clingo_name

        for executor, cpu_list in executor_cpu_constraints.items():
            executor_name = executor.get_name()
            for cpu in cpu_list:
                cpu_id = cpu.get_id()
                print("ex_cpu(" + clingo(executor_name) + ", " + clingo(cpu_id) + ").")

    @staticmethod
    def print_cache_isolation_domains(cache_isolation_domains):
        clingo = PageColoringModelClingoPrinter.convert_to_clingo_name

        print("cache_isolation_domain(1.." + str(len(cache_isolation_domains)) + ").")

        for i, memory_regions in enumerate(cache_isolation_domains, start=1):
            for memory_region in memory_regions:
                mr = memory_region
                if isinstance(mr, Channel):
                    source_name = clingo(mr.get_source().get_name())
                    target_name = clingo(mr.get_target().get_name())

                    mr_name = "c(" + source_name + ", " + target_name + ")"
                else:
                    mr_name = clingo(mr.get_name())

                print("mr_cache_isolation(" + mr_name + ", " + str(i) + ").")

    @staticmethod
    def print_cache_colors(system: System):
        # TODO: Hardcoded, Refactor.
        cache_information = system.get_hardware().get_cache_information()
        l1 = cache_information[0]
        l2 = cache_information[1]
        l3 = cache_information[2]

        l1_colors = l1.get_number_of_colors()
        l2_colors = l2.get_number_of_colors()
        l3_colors = l3.get_number_of_colors()

        # Assumption: Cache color can only be bound either to none or to only one CPU (not to several CPUs).
        # #ASSMS-CACHE-CONFIG-X
        l1_str = "l1_color(1.." + str(l1_colors) + (", CPU) :- cpu(CPU)." if not l1.get_shared() else ").")
        l2_str = "l2_color(1.." + str(l2_colors) + (", CPU) :- cpu(CPU)." if not l2.get_shared() else ").")
        l3_str = "l2_color(1.." + str(l3_colors) + (", CPU) :- cpu(CPU)." if not l3.get_shared() else ").")

        print(l1_str)
        print(l2_str)
        print(l3_str)

    @staticmethod
    def print_page_colors(system: System):
        cache_information = system.get_hardware().get_cache_information()
        l1_shared = cache_information[0].get_shared()
        l2_shared = cache_information[1].get_shared()
        l3_shared = cache_information[2].get_shared()

        # TODO: Refactor, also see #ASSMS-CACHE-CONFIG-X
        for page_color in system.get_page_colors():
            l1 = page_color.get_cache_colors()[0]
            l2 = page_color.get_cache_colors()[1]
            l3 = page_color.get_cache_colors()[2]
            l1_color = l1.get_id()
            l2_color = l2.get_id()
            l3_color = l3.get_id()
            for cpu in system.get_hardware().get_cpu_cores():
                cpu_name = cpu.get_id()

                l1_str = "l1_color({})".format(l1_color if l1_shared else l1_color + ", " + cpu_name)
                l2_str = "l2_color({})".format(l2_color if l2_shared else l2_color + ", " + cpu_name)
                l3_str = "l3_color({})".format(l3_color if l3_shared else l3_color + ", " + cpu_name)

                output_str = "page_color({}, {}, {}).".format(l1_str, l2_str, l3_str)

                print(output_str)
