#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
from typing import List, Dict, Set  # need this for specifying List/Dict/Set types for type hints

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

"""
This script models certain aspects of a page-coloring algorithm which will be
integrated into a separation kernel (SK) build system.
"""


# TODO: Specification of bootstrap processor needed?
class Hardware:
    """Description of a hardware system which consists of CPU cores, main memory and (multiple layers) of caches."""

    class CPU:
        cpu_namespace = []
        cpu_ctr = 0

        def __init__(self, name: str = None):
            if name is None:
                name = str(Hardware.CPU.cpu_ctr)
                Hardware.CPU.cpu_ctr += 1
            assert name not in Hardware.CPU.cpu_namespace, "CPU core names must be unique."
            Hardware.CPU.cpu_namespace.append(name)
            self.name = name

        def __str__(self):
            return "CPU_" + self.name

    class CPUCacheConfig:
        def __init__(self,
                     caches: List[List['Cache']],
                     cpu_cores: List['CPU'],
                     cache_cpu_mappings: List[Dict['Cache', 'CPU']]):
            """
            Args:
                caches: List of list of caches, where the first element designates the list of L1 caches,
                the second element, designates the list of L2 caches, etc.
                cpu_cores: List of CPU cores of the system.
                cache_cpu_mappings: List of mappings (in form of a dictionary) from a cache to a CPU core.
                The first element designates the mappings of the L1 caches, the second element the mappings of the L2
                caches etc.
            """

            all_caches_of_all_levels = [cache for caches_of_one_level in caches for cache in caches_of_one_level]
            assert len(all_caches_of_all_levels) == len(set(all_caches_of_all_levels)), "All caches must be unique."
            assert len(cpu_cores) == len(set(cpu_cores)), "All CPU cores must be unique."
            assert len(caches) == len(cache_cpu_mappings),\
                "Number of cache levels (L1, L2, ...) is number of mappings (L1->CPU, L2->CPU, ...)."
            all_mappings_in_one_dict = \
                {cache: cpu for mapping in cache_cpu_mappings for cache, cpu in mapping.items()}
            assert all((cache in all_mappings_in_one_dict) for cache in all_caches_of_all_levels),\
                "Each cache must be assigned to a CPU core."

            # We also assume that the caches of one cache level are structurally the same.
            # So it's forbidden to have one L1 cache which is flushed, while others are not flushed,
            # or one L2 cache which has a cacheline_capacity of 64, while another L2 cache has not.
            # #ASSMS-STRUCTURALLY-SAME-CACHES-ONE-SAME-LEVEL-1

            self.caches = caches
            self.cpu_cores = cpu_cores
            self.cpu_cache_mappings = cache_cpu_mappings

        def get_caches(self):
            """
            Returns:
                List[List[Cache]]: The list of list of caches.
            """
            return self.caches

        def get_cpu_cores(self):
            """
            Returns:
                List[CPU] : List of cpu cores.
            """
            return self.cpu_cores

    class SystemPageColor:
        """A system page color is a tuple of CPU and int whereas the first element designates a CPU core
        and the second element designates a usable page color.

        E. g. (CPU_0, 0), (CPU_1, 3), (CPU_3, 127) are valid system page colors on a system with three CPU cores
        and 128 usable page colors."""
        def __init__(self, cpu: 'Hardware.CPU', page_color: int):
            self.cpu = cpu
            self.page_color = page_color

        def __str__(self):
            return str((str(self.cpu), self.page_color))

        def __hash__(self):
            return hash(str(self))

        def __eq__(self, other):
            return (isinstance(other, Hardware.SystemPageColor) and
                    self.cpu == other.cpu and self.page_color == other.page_color)

    def __init__(self, cpu_cache_config: CPUCacheConfig, page_size: int=4096):
        """
        Args:
            cpu_cache_config: Complex data structure which describes CPU cores, caches and their mappings to the
            CPU cores.
            page_size: Page size in bytes.
        """
        # TODO: Implement initialization
        self.cpu_cache_config = cpu_cache_config

    def get_number_of_usable_colors(self):
        """
        Returns the number of page colors which can practically be used to separate execution contexts/subjects to
        mitigate cache side-channels. Note that this number does not reflect maximum number of page colors
        when only considering the biggest last-level cache.

        Returns:
            int: Number of page colors which can practically be used to separate execution contexts/subjects.
        """
        colors_of_one_cache = 0
        for caches_of_same_level in self.cpu_cache_config.get_caches():
            colors_of_one_cache = caches_of_same_level[0].get_colors()
            if caches_of_same_level[0].get_flushed():
                continue
            else:
                break

        assert colors_of_one_cache > 0
        return colors_of_one_cache*len(self.cpu_cache_config.get_cpu_cores())

    def get_all_system_page_colors(self):
        """Returns the list of all system page colors sorted by page color (int).

        Returns:
            List[SystemPageColor]: List of all system page colors sorted by page color (int), so that it's easy to
                distribute system page colors of all CPU core equally:
                (CPU_0,0), (CPU_1,0), (CPU_0, 1), (CPU_1, 1), ...
        """
        # (CPU_0,0), (CPU_1,0), (CPU_0, 1), (CPU_1, 1), ...
        all_system_page_colors = [Hardware.SystemPageColor(cpu, color)
                                  for color in range(self.get_number_of_usable_colors())
                                  for cpu in self.cpu_cache_config.get_cpu_cores()]
        return all_system_page_colors

    def get_cpu_cores(self):
        return self.cpu_cache_config.get_cpu_cores()


class Cache:
    """Description of a CPU cache."""

    def __init__(self, total_capacity: int, associativity: int, cacheline_capacity: int, flushed: bool = False,
                 page_size: int = 4096):
        """
        Args:
            total_capacity: Total capacity of cache in bytes.
            associativity: Number of cache lines of a set in a cache.
            cacheline_capacity: Number of Bytes a cache line can store.
            flushed: True if cache is flushed on context/subject switch. This effectively enables the usage of
                colors of higher level caches.
            page_size: Page size in bytes.
        """
        self.flushed = flushed
        self.total_capacity = total_capacity
        self.associativity = associativity
        self.cacheline_capacity = cacheline_capacity
        self.sets = self.total_capacity / (self.associativity * self.cacheline_capacity)

        # The access of one page frame affects several sets of a cache.
        # The number of these affected sets depends not only on the page size
        # and the cache line capacity but also on the mapping of physical memory to cache lines.
        # We assume that the first $cacheline_capacity bytes of the page frame is allocated
        # to the first set of the cache, the second $cacheline_capacity bytes to
        # the second set etc. #ASSMS-CACHE-MAPPING
        self.affected_sets_per_page = page_size / self.cacheline_capacity

        # All by one page frame affected sets are assigned to one color.
        # We assume that a page frame owns the whole affected set even if it actually
        # uses only one cache line of it.
        # Depending on the replacement policy of the cache you in theory could use the
        # other cache lines for other colors as long other consumed cache lines aren't replaced.
        # So we assume a strict form of "coloring strategy" here. #ASSMS-COLORING-STRATEGY
        self.colors = self.sets / (page_size / self.cacheline_capacity)

        # We assume that all numbers defined here must be integer (no floats), otherwise there is something wrong
        # #ASSMS-CACHE-PROPS-ONLY-INTS
        assert (self.sets.is_integer()), "#ASSMS-CACHE-PROPS-ONLY-INTS"
        assert (self.affected_sets_per_page.is_integer()), "#ASSMS-CACHE-PROPS-ONLY-INTS"
        assert (self.colors.is_integer()), "#ASSMS-CACHE-PROPS-ONLY-INTS"
        self.sets = int(self.sets)
        self.affected_sets_per_page = int(self.affected_sets_per_page)
        self.colors = int(self.colors)

    def get_colors(self):
        return self.colors

    def get_flushed(self):
        return self.flushed


class Executor:
    """Designates entities which are executed on the system (e. g. kernel, subjects)."""
    def __init__(self):
        self.classification = None
        self.compartment = None

    def set_security_label(self, classification: int, compartment: Set[int]):
        """
        Set the security label of an executable entity. The assignment of security labels to executable entities
        effectively establishes a lattice of security labels which establishes a security hierarchy between
        labeled entities. A security label can be constructed from a classification and a set of codewords which
        defines a compartment.
        Entity_X has a higher or equal security clearance than Entity_Y
            <=> Entity_X.classification <= Entity_X.classification AND
                Entity_X.compartment is the same set or a proper superset of Entity_Y.compartment

        Args:
            classification: The classification of the executable entity. The *lower* the higher the classification.
                E. g. use 0=TOP SECRET, 1=SECRET, 2=UNCLASSIFIED, ...
            compartment: Set of codewords which defines a compartment.
                E. g. use something like {0, 1, 2} for {CRYPTO, FOREIGN, SECRET_PROJECTX}, and
                {0,2} for {CRYPTO, SECRET_PROJECTX}
        """
        self.classification = classification
        self.compartment = compartment

    def get_security_label(self):
        assert (self.classification is not None) and (self.compartment is not None),\
            "Classification and compartment must both be defined."
        return self.classification, self.compartment


class MemoryConsumer:
    """A MemoryConsumer represents memory consuming objects like subjects or channels.

    A MemoryConsumer consumes certain memory of size $memsize > 0
    and may get assigned an address space of size $memsize and a color
    for this address space.
    """

    def __init__(self, memsize: int, page_size: int = 4096):
        """
        Args:
            memsize: Memory size of memory consumer in bytes.
            page_size: Page size in bytes.
        """
        assert memsize % page_size == 0, "Memory size of memory consume must be a multiple of page size."
        assert memsize > 0, "Memory size must be positive."

        self.address_space = None
        self.memsize = memsize
        self.color = None

    def set_color(self, color: Hardware.SystemPageColor):
        self.color = color

    def get_color(self):
        return self.color

    def set_address_space(self, address_space: List[range]):
        assert len(address_space) > 0, "There must be at least one range of addresses specified."
        assert MemoryConsumer.__address_space_size(address_space) == self.memsize,\
            "Size of specified address space must comply to the memory requirement/size of the MemoryConsumer."
        assert MemoryConsumer.__address_space_not_overlapping(address_space),\
            "Address ranges must not be overlapping."

        self.address_space = address_space

    @staticmethod
    def __address_space_size(address_space: List[range]) -> int:
        size = 0
        for mem_range in address_space:
            size += len(mem_range)

        return size

    @staticmethod
    def __address_space_not_overlapping(address_space: List[range]) -> bool:
        # union of all addresses of address space
        union = set().union(*address_space)
        # number of addresses of each memory range in address space
        n = sum(len(mem_range) for mem_range in address_space)

        return n == len(union)

    def get_address_space(self):
        return self.address_space


# We assume that Kernel memory pages can also be colored easily. #ASSMS-KERNEL-PAGE-COLORING
class Kernel(MemoryConsumer, Executor):
    pass


class Subject(MemoryConsumer, Executor):
    """A subject represents a running instance of a component on top of a SK.

    It has a memory requirement (in Byte) and may have channels to other subjects.
    """

    def __init__(self, memsize):
        super().__init__(memsize)

        self.inchannels: Dict[Subject, List[Channel]] = {}
        self.outchannels: Dict[Subject, List[Channel]] = {}

    def add_inchannel(self, channel: 'Channel'):
        from_subject = channel.get_source()
        if from_subject not in self.inchannels:
            self.inchannels[from_subject] = [channel]
        else:
            self.inchannels[from_subject].append(channel)

    def add_outchannel(self, channel: 'Channel'):
        to_subject = channel.get_target()
        if to_subject not in self.outchannels:
            self.outchannels[to_subject] = [channel]
        else:
            self.outchannels[to_subject].append(channel)

    def get_channels(self):
        """Returns all in and out channels of this subject.

        Returns:
            List[Channels]: List of all channels of subject.
        """
        all_inchannels = [channel for channel_list in self.inchannels.values() for channel in channel_list]
        all_outchannels = [channel for channel_list in self.outchannels.values() for channel in channel_list]
        return all_inchannels + all_outchannels

    def get_inoutchannels(self, subject: 'Subject'):
        """Returns all out channels to given subject and all in channels from given subject.

        Returns:
            List[Channel]: All out channels to given subject and all in channels from given subject.
        """
        return self.inchannels[subject] + self.outchannels[subject]


class Channel(MemoryConsumer):
    """A channel represents an unidirectional communication relationship between
    a source subject and a target subject and as well has a memory requirement (in Byte).
    """

    def __init__(self, memsize, source: Subject, target: Subject):
        super().__init__(memsize)
        self.source = source
        self.target = target

        source.add_outchannel(self)
        target.add_inchannel(self)

    def get_source(self):
        return self.source

    def get_target(self):
        return self.target


###############################################################################

def print_memory_consumer(all_memory_consumers: Dict[str, MemoryConsumer]) -> None:
    def print_bar():
        print("=" * 74)

    fmt1 = '{0: <45}'  # format string with width 20
    fmt2 = '{0: <10}'

    print_bar()
    print(fmt1.format('Memory Consumer') + ' : ' + fmt2.format('Color') + ' : ' + fmt2.format('Address Space'))
    print_bar()
    for name, memory_consumer in all_memory_consumers.items():
        print(fmt1.format(name) + " : "
              + fmt2.format(str(memory_consumer.get_color())) + ' : '
              + fmt1.format(str(memory_consumer.get_address_space())))
    print_bar()
    # TODO: Print number of used and unassigned colors.


class ColorAssigner:
    """Responsible for assigning colors to MemoryConsumers.

    They're currently four assignment methods:
    1. naive: Just distribute system page colors to each memory consumer so that each CPU cores
              are distributed equally to the memory consumers. It's equivalent when using the interference domains
              method with an empty interference domains list.
    2. with interference domains: Specify sets of memory consumers which may interfere which each other.
    3. with security labels: Assign system page colors according to the security labels of the memory consumers
                             so that no memory consumer can cache-interfere with higher-clearance memory consumers
                             and no memory consumer can cache-interfere with memory consumers with different
                             compartment.
    4. with cache isolation domains: TODO
    """

    class ColorExhaustion(Exception):
        def __init__(self):
            default_message = "There are not enough colors to distribute. "\
                              "Maybe another color assignment method can help."
            super().__init__(default_message)

    @staticmethod
    def reset_colors(all_memory_consumers: Dict[str, MemoryConsumer]):
        for memory_consumer in all_memory_consumers.values():
            memory_consumer.set_color(None)

    @staticmethod
    def get_assignment_by_naive(hardware: Hardware, all_memory_consumers: Dict[str, MemoryConsumer]) -> \
            Dict[MemoryConsumer, Hardware.SystemPageColor]:

        assignment = {}

        num_assignable_colors = hardware.get_number_of_usable_colors()
        num_required_colors = len(all_memory_consumers)
        all_system_page_colors = hardware.get_all_system_page_colors()

        if num_required_colors > num_assignable_colors:
            raise ColorAssigner.ColorExhaustion()
        else:
            for memory_consumer, color in zip(all_memory_consumers.values(), all_system_page_colors):
                assignment[memory_consumer] = color

        return assignment

    @staticmethod
    def assign_by_naive(hardware: Hardware, all_memory_consumers: Dict[str, MemoryConsumer]):
        """
        Distributes - if possible - system page colors to all memory consumers by iterating through all system page
        colors and distributing colors from all CPU cores equally. Raises an exception if it's not possible.

        Raises:
            ColorAssigner.ColorExhaustion: There are not enough colors to distribute.
        """
        assignment = ColorAssigner.get_assignment_by_naive(hardware, all_memory_consumers)
        ColorAssigner._enforce_assignment(assignment)

    @staticmethod
    def assign_color_by_interference_domains(hardware: Hardware, all_memory_consumers: Dict[str, MemoryConsumer],
                                             interference_domains: List[Set[MemoryConsumer]]):
        """Assign colors by interference domains.

        This function does not respect pre-assigned colors of memory consumers. All memory consumer colors
        must be undefined (None) at beginning of assignment.

        Args:
            hardware:
            all_memory_consumers:
            interference_domains: An interference domain is a set of memory consumers whose memory regions are allowed
                to interfere with each others in cache(s). Interference domains effectively lead to less color usage
                since members of the same interference domain may share the same color. Non specified memory consumers
                get exclusive colors.
        Raises:
            ColorAssigner.ColorExhaustion: There are not enough colors to distribute.
        """
        #       1. iterate through interference domains
        #           1. assign same color to memory consumers in same interference domain
        #              (if a memory consumer was colored before, its color gets overwritten)
        #           2. remove colored memory consumers from all_memory_consumers
        #           3. increase assigned_color_counter to later assure
        #              it is small than the number of all assignable colors
        #           4. If assigned_color_counter >= number of all assignable colors
        #              return EXCEPTION (color exhaustion)
        #       2. assign rest of colors incrementally to rest of all_memory_consumers and
        #          assure that there is no color exhaustion
        assert all((memory_consumer.get_color() is None) for memory_consumer in all_memory_consumers.values()),\
            "The colors of all memory consumers must be undefined."

        def get_next_assignable_color(table: Dict[Hardware.SystemPageColor, int]):
            for color, counter in table.items():
                if counter == 0:
                    return color

            raise ColorAssigner.ColorExhaustion()

        all_memory_consumers_values = list(all_memory_consumers.values())
        color_usage_counter_table = {color: 0 for color in hardware.get_all_system_page_colors()}

        for interference_domain in interference_domains:
            assignable_color = get_next_assignable_color(color_usage_counter_table)
            for memory_consumer in interference_domain:
                if memory_consumer.get_color() is not None:
                    color_usage_counter_table[memory_consumer.get_color()] -= 1

                memory_consumer.set_color(assignable_color)
                color_usage_counter_table[assignable_color] += 1

                all_memory_consumers_values.remove(memory_consumer)

        # assign colors to rest of all_memory_consumers_values
        for memory_consumer in all_memory_consumers_values:
            assignable_color = get_next_assignable_color(color_usage_counter_table)
            memory_consumer.set_color(assignable_color)
            color_usage_counter_table[assignable_color] += 1

    @staticmethod
    def get_assignment_by_security_labels(hardware: Hardware, all_executors: Dict[str, Executor]) \
            -> Dict[MemoryConsumer, Hardware.SystemPageColor]:
        return {}

    @staticmethod
    def assign_color_by_security_labels(hardware: Hardware, all_executors: Dict[str, Executor]):
        assignment = ColorAssigner.get_assignment_by_security_labels(hardware, all_executors)
        ColorAssigner._enforce_assignment(assignment)

    @staticmethod
    def get_assignment_by_cache_isolation_domains(
            hardware: Hardware,
            all_memory_consumers: Dict[str, MemoryConsumer],
            cache_isolation_domains: List[Set[MemoryConsumer]],
            executor_cpu_constraints: Dict[Executor, Set[Hardware.CPU]] = None,
            cpu_access_constraints: Dict[Hardware.CPU, Executor] = None
    ) \
            -> Dict[MemoryConsumer, Hardware.SystemPageColor]:
        return {}

    @staticmethod
    def assign_by_cache_isolation_domains(
            hardware:                   Hardware,
            all_memory_consumers:       Dict[str, MemoryConsumer],
            cache_isolation_domains:    List[Set[MemoryConsumer]],
            executor_cpu_constraints:   Dict[Executor, Set[Hardware.CPU]] = None,
            cpu_access_constraints:     Dict[Hardware.CPU, Executor] = None
    ):
        """

        Args:
            hardware:
            all_memory_consumers:
            cache_isolation_domains:
            executor_cpu_constraints:
            cpu_access_constraints:

        Returns:

        """
        assignment = ColorAssigner.get_assignment_by_cache_isolation_domains(
            hardware, all_memory_consumers, cache_isolation_domains, executor_cpu_constraints, cpu_access_constraints
        )
        ColorAssigner._enforce_assignment(assignment)

    @staticmethod
    def _enforce_assignment(assignment: Dict[MemoryConsumer, Hardware.SystemPageColor]):
        for memory_consumer, color in assignment.items():
            memory_consumer.set_color(color)

