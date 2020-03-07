from page_coloring_model import *


class PageColoringModelPrettyPrinter:
    format_column_cache_isolation_domain_members = '{0: <45}'
    format_column_number = '{0: <2}'
    format_column_type = '{0: <7}'
    format_column_name = '{0: <45}'
    format_column_memory_size = '{0: <11}'
    format_column_colors = '{0: <10}'
    format_column_pages = '{0: <11}'

    @staticmethod
    def print_bar():
        print("=" * 120)

    @staticmethod
    def print_memory_regions(system: System) -> None:
        fmt0 = PageColoringModelPrettyPrinter.format_column_type
        fmt1 = PageColoringModelPrettyPrinter.format_column_name
        fmt2 = PageColoringModelPrettyPrinter.format_column_memory_size

        PageColoringModelPrettyPrinter.print_bar()
        print(fmt0.format('Type') + ' | ' + fmt1.format('Name') + ' | ' + fmt2.format('Memory size'))
        PageColoringModelPrettyPrinter.print_bar()
        for memory_region in system.get_memory_regions():
            print(fmt0.format(str(type(memory_region).__name__))
                  + ' | ' + fmt1.format(memory_region.get_name())
                  + ' | ' + fmt2.format(memory_region.get_memory_size())
                  )
        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_cache(cache: Cache):
        # import inspect
        PageColoringModelPrettyPrinter.print_bar()
        print("Total capacity: " + str(cache._total_capacity))
        print("Associativity: " + str(cache._associativity))
        print("Cacheline capacity: " + str(cache._cacheline_capacity))
        print("Shared: " + str(cache._shared))
        print("Flushed: " + str(cache.get_flushed()))
        print("Number of Colors: " + str(cache.get_number_of_colors()))
        # print("Index function: " + str(inspect.getsource(cache.get_index_function())).rstrip())
        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_color_assignment(system: System):
        fmt0 = PageColoringModelPrettyPrinter.format_column_type
        fmt1 = PageColoringModelPrettyPrinter.format_column_name
        fmt2 = PageColoringModelPrettyPrinter.format_column_colors

        PageColoringModelPrettyPrinter.print_bar()
        print(fmt0.format('Type') + ' | ' + fmt1.format('Name') + ' | ' + fmt2.format('Color(s)'))
        PageColoringModelPrettyPrinter.print_bar()

        for memory_region in system.get_memory_regions():
            print(fmt0.format(str(type(memory_region).__name__))
                  + ' | ' + fmt1.format(memory_region.get_name())
                  + ' | ', end=''
                  )
            for color in memory_region.get_colors():
                print(fmt2.format(str(color)))
                print(fmt0.format("")
                      + ' | ' + fmt1.format("")
                      + ' | ', end=''
                      )
            print("")
        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_cache_isolation_domains(cache_isolation_domains: List[Set[MemoryRegion]]):
        fmt0 = PageColoringModelPrettyPrinter.format_column_number
        fmt1 = PageColoringModelPrettyPrinter.format_column_cache_isolation_domain_members

        PageColoringModelPrettyPrinter.print_bar()
        print(fmt0.format('#') + ' | ' + fmt1.format('Cache isolation domain members'))
        PageColoringModelPrettyPrinter.print_bar()

        cid_num = 1
        for cache_isolation_domain in cache_isolation_domains:
            print(fmt0.format(str(cid_num)) + ' | ', end='')
            for member in cache_isolation_domain:
                print('(' + str(member._name) + ')', end=' ')

            print("")
            cid_num += 1

        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_executor_cpu_constraints(executor_cpu_constraints: Dict[MemoryRegion, Set[Hardware.CPU]]):
        fmt0 = '{0: <25}'
        fmt1 = '{0: <50}'

        PageColoringModelPrettyPrinter.print_bar()
        print(fmt0.format('Executor') + ' | ' + fmt1.format('Assigned CPU(s)'))
        PageColoringModelPrettyPrinter.print_bar()
        for executor, assigned_cpu_cores in executor_cpu_constraints.items():
            print(fmt0.format(str(executor.get_name())) + ' | ', end='')
            for cpu_core in assigned_cpu_cores:
                print('(' + str(cpu_core) + ')', end=' ')

            print("")

        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_unassigned_system_page_colors(system: System, assignment: Dict[Hardware.SystemPageColor, Set[MemoryRegion]]):
        # Assumption: All SystemPageColors are contained in assignment.keys()

        assert (all(spc in assignment.keys() for spc in system.get_system_page_colors()))

        PageColoringModelPrettyPrinter.print_bar()

        num_unassigned_colors = 0
        for system_page_color, assignees in assignment.items():
            if len(assignees) == 0:
                num_unassigned_colors += 1
                print(system_page_color)

        print("Number of unassigned system page colors: " + str(num_unassigned_colors)
              + " (of " + str(len(system.get_system_page_colors())) + ')')

        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_cpu_cache_config(cpu_cache_config: Hardware.CPUCacheConfig):
        PageColoringModelPrettyPrinter.print_bar()

        for level, mapping in enumerate(cpu_cache_config.cpu_cache_mappings, start=1):
            print("Mappings of Level " + str(level) + " caches:")
            mapping_str = ''.join('(' + str(cpu) + ', ' + str(cache) + ')' for cpu, cache in mapping)
            print(mapping_str)
            level += 1

        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_cache_colors(system: System):
        PageColoringModelPrettyPrinter.print_bar()

        for level, cache_colors_of_one_level in enumerate(system.get_cache_colors(), start=1):
            logging.info("L" + str(level) + " cache colors:")
            PageColoringModelPrettyPrinter.print_bar()
            for cache_colors in cache_colors_of_one_level.values():
                print(str(cache_colors))
            PageColoringModelPrettyPrinter.print_bar()

        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_page_colors(system: System):
        PageColoringModelPrettyPrinter.print_bar()
        for page_color in system.get_page_colors():
            print(str(page_color))
        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_system_page_colors(system: System):
        PageColoringModelPrettyPrinter.print_bar()

        for system_page_color in system.get_system_page_colors():
            print(system_page_color, end="\n")
        print("")

        PageColoringModelPrettyPrinter.print_bar()

    @staticmethod
    def print_page_assignment(system: System) -> None:
        fmt0 = PageColoringModelPrettyPrinter.format_column_type
        fmt1 = PageColoringModelPrettyPrinter.format_column_name
        fmt2 = PageColoringModelPrettyPrinter.format_column_memory_size
        fmt3 = PageColoringModelPrettyPrinter.format_column_pages

        PageColoringModelPrettyPrinter.print_bar()
        print(fmt0.format('Type') + ' | '
              + fmt1.format('Name')
              + ' | '
              + fmt2.format('Memory size')
              + ' | '
              + fmt3.format('Pages')
        )
        PageColoringModelPrettyPrinter.print_bar()
        for memory_region in system.get_memory_regions():
            print(fmt0.format(str(type(memory_region).__name__))
                  + ' | ' + fmt1.format(memory_region.get_name())
                  + ' | ' + fmt2.format(memory_region.get_memory_size())
                  + ' | ' + fmt3.format(str(memory_region.get_pages()))
                  )
        PageColoringModelPrettyPrinter.print_bar()
