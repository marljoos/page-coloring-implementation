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
            if name is None:  # if name is not specified, name is "CPU_$cpu_ctr"
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
                     cpu_cores: List['Hardware.CPU'],
                     cache_cpu_mappings: List[Dict['Cache', 'Hardware.CPU']],
                     complex_indexing: bool = False  # TODO: Currently not supported, maybe assigning indexing function
                                                     # instead of boolean
        ):
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
        and the second element designates a CPU page color.

        Note the difference (CPU_0, 3) is a possible SystemPageColor, whereas 3 is the CPU page color, which indexes
        a page color within a CPU core.

        E. g. (CPU_0, 0), (CPU_1, 3), (CPU_3, 127) are valid system page colors on a system with three CPU cores
        and 128 CPU page colors."""
        def __init__(self, cpu: 'Hardware.CPU', cpu_page_color: int):
            self.cpu = cpu
            self.cpu_page_color = cpu_page_color

        def __str__(self):
            return str((str(self.cpu), self.cpu_page_color))

        def __hash__(self):
            return hash(str(self))

        def __eq__(self, other):
            return (isinstance(other, Hardware.SystemPageColor) and
                    self.cpu == other.cpu and self.cpu_page_color == other.cpu_page_color)

        def get_cpu(self):
            return self.cpu

        def get_cpu_page_color(self):
            return self.cpu_page_color

    def __init__(self, cpu_cache_config: CPUCacheConfig, page_size: int = 4096):
        """
        Args:
            cpu_cache_config: Complex data structure which describes CPU cores, caches and their mappings to the
            CPU cores.
            page_size: Page size in bytes.
        """
        # TODO: Implement initialization
        self.cpu_cache_config = cpu_cache_config

    def get_number_of_cpu_page_colors(self) -> int:
        """
        Returns the number of CPU page colors of the system.

        So if the system has 4 CPU cores, an one CPU core has SystemPageColors from (CPU_X, 0) to (CPU_X, 127) the
        system has 128 CPU page colors.

        Note this is not the number of all usable system page colors of the system.
        """

        colors_of_one_cache = 0
        for caches_of_same_level in self.cpu_cache_config.get_caches():
            colors_of_one_cache = caches_of_same_level[0].get_colors()
            if caches_of_same_level[0].get_flushed():
                continue
            else:
                break

        assert colors_of_one_cache > 0
        return colors_of_one_cache

    def get_number_of_system_page_colors(self) -> int:
        # number of system page colors is number of cpu page colors times the number of CPU cores
        number_of_system_page_colors = self.get_number_of_cpu_page_colors() * len(self.get_cpu_cores())
        return number_of_system_page_colors

    def get_all_system_page_colors(self):
        """Returns the list of all system page colors sorted by page color (int).

        Returns:
            List[SystemPageColor]: List of all system page colors sorted by page color (int), so that it's easy to
                distribute system page colors of all CPU core equally:
                (CPU_0,0), (CPU_1,0), (CPU_0, 1), (CPU_1, 1), ...
        """
        # (CPU_0,0), (CPU_1,0), (CPU_0, 1), (CPU_1, 1), ...
        all_system_page_colors = [Hardware.SystemPageColor(cpu, cpu_page_color)
                                  for cpu_page_color in range(self.get_number_of_cpu_page_colors())
                                  for cpu in self.cpu_cache_config.get_cpu_cores()]
        return all_system_page_colors

    def get_cpu_cores(self):
        return self.cpu_cache_config.get_cpu_cores()


class Cache:
    """Description of a CPU cache."""

    def __init__(self,
                 total_capacity: int,
                 associativity: int,
                 cacheline_capacity: int,
                 shared: bool = False,  # TODO: documentation,
                 flushed: bool = False,
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
    A MemoryConsumer may also have a list of Executors which are accessing (read/write/execute) the memory region.
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
        self.executors: List[Executor] = []
        self.colors = []

    def reset_colors(self):
        self.colors = []

    def add_color(self, color: Hardware.SystemPageColor):
        self.colors.append(color)

    def get_colors(self):
        return self.colors

    def add_executor(self, executor: Executor):
        self.executors.append(executor)

    def get_executors(self):
        return self.executors

    def set_address_space(self, address_space: List[range]):
        def __address_space_size(address_space: List[range]) -> int:
            size = 0
            for mem_range in address_space:
                size += len(mem_range)

            return size

        def __address_space_not_overlapping(address_space: List[range]) -> bool:
            # union of all addresses of address space
            union = set().union(*address_space)
            # number of addresses of each memory range in address space
            n = sum(len(mem_range) for mem_range in address_space)

            return n == len(union)

        assert len(address_space) > 0, "There must be at least one range of addresses specified."
        assert __address_space_size(address_space) == self.memsize,\
            "Size of specified address space must comply to the memory requirement/size of the MemoryConsumer."
        assert MemoryConsumer.__address_space_not_overlapping(address_space),\
            "Address ranges must not be overlapping."

        self.address_space = address_space

    def get_address_space(self):
        return self.address_space


# We assume that Kernel memory pages can also be colored easily. #ASSMS-KERNEL-PAGE-COLORING
class Kernel(MemoryConsumer, Executor):
    def __init__(self, memsize):
        super().__init__(memsize)

        self.add_executor(self)


class Subject(MemoryConsumer, Executor):
    """A subject represents a running instance of a component on top of a SK.

    It has a memory requirement (in Byte) and may have channels to other subjects.
    """

    def __init__(self, memsize):
        super().__init__(memsize)

        self.inchannels: Dict[Subject, List[Channel]] = {}
        self.outchannels: Dict[Subject, List[Channel]] = {}

        self.add_executor(self)

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
        Raises: TODO: Raises exception if there is no in or out channel from/to subject.
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

        self.add_executor(source)
        self.add_executor(target)

    def get_source(self):
        return self.source

    def get_target(self):
        return self.target


###############################################################################

def print_memory_consumer(all_memory_consumers: Dict[str, MemoryConsumer]) -> None:
    def print_bar():
        print("=" * 85)

    fmt1 = '{0: <45}'
    fmt2 = '{0: <10}'

    print_bar()
    print(fmt1.format('Memory Consumer')
          + ' : ' + fmt2.format('Color(s)')
    #     + ' : ' + fmt2.format('Address Space')
          )
    print_bar()
    for name, memory_consumer in all_memory_consumers.items():
        colors = ''.join(str(color) for color in memory_consumer.get_colors())
        print(fmt1.format(name)
              + ' : ' + fmt2.format(colors)
        #     + ' : ' + fmt1.format(str(memory_consumer.get_address_space()))
              )
    print_bar()
    # TODO: Print number of used and unassigned colors.


# TODO: move to System class
def print_channels():
    pass


# TODO: move to System class
def print_system_page_colors_address_spaces(system_page_colors):
    # params:
    # - list of colors, ordered;
    #   - need specification of ordering of colors,
    #   - is (CPU_1, 0) color 2 (after (CPU_0, 0) ) or color 9 (color after (CPU_0, $LAST_CPU_PAGE_COLOR) )
    # - MEMSIZE / MEMRANGES
    # - complex indexing / indexing function
    def print_bar():
        print("=" * 85)

    # address_space: List[range]

    def assign_address_spaces(system_page_colors):
        """
        Example for 32 bit addresses:

        1098765432109 87654 32109876 543210
                      |   |  |     | |    |
                      |   |  |     | +--->+--> Depending on cache line size (here assuming 64 Bytes):
                      |   |  |     |           - Bit 0 to Bit 5: Bytes within cache line
                      |   |  |     |
                      |   |  +-----|---------> Depending on page size (here assuming 4096 bytes (taking 12 bits):
                      |   |        |           - From Bit 12 to MSB: Real page frame index which can be used for
                      |   |        |             assigning page frames
                      |   |        |             - These bits without System Page Color index bits:
                      |   |        |               -> Logical page frame index
                      |   |        |
                      +------------+---------> Depending on the number of sets of the last level cache
                      |   |                       (here assuming 8192 sets of the L3 cache -> 13 Bits):
                      |   |                    - Bit 6 to Bit 18: Set index (enumerates the sets of the L3 cache)
                      |   |
                      +---+------------------> Depending on the size of the Set index and the number of
                                                System Page Colors
                                                  (here assuming a Set index width of 13 Bits, and 32 (5 Bits) as number
                                                   of all System Page Colors, e. g. a 4 CPU core system with 8 CPU Page
                                                   Colors from (CPU_0, 0) to (CPU_3, 7) )
                                               - Bit 14 to Bit 18: System Page Color index
                                                      (used to map System Page Colors to assignable address ranges)
                                                 - SystemPageColors'BitWidth most significant bits of Set index

        Example mapping of System Page Color to address ranges (assuming (CPU_0, 0) has color index 0) using a bitmask:
                      1098765432109 87654 32109876 543210
        (CPU_0, 0) -> XXXXXXXXXXXXX 00000 XX------ ------
           ...
        (CPU_3, 7) -> XXXXXXXXXXXXX 11111 XX------ ------

            All X's comprises the logical page frame index. So the first page frame which can be used by (CPU_0, 0) is
            1098765432109 87654 32109876 543210
            0000000000000 00000 00------ ------
            and the last page frame which can be used by (CPU_0, 0) is
            1098765432109 87654 32109876 543210
            1111111111111 00000 11------ ------

        Args:
            system_page_colors:

        Returns:

        """
        mapping = {system_page_color: set() for system_page_color in system_page_colors}

        # TODO: no hardcoded stuff
        import math
        all_bits = 32  # 32-bit address space
        cache_line_size = 64
        num_llc_sets = 8192
        num_system_page_colors = len(system_page_colors)
        page_size = 4096

        cache_line_bits = int(math.log2(cache_line_size))
        set_index_bits = int(math.log2(num_llc_sets))
        color_index_bits = int(math.log2(num_system_page_colors))

        msb_color_index = cache_line_bits + set_index_bits
        lsb_color_index = msb_color_index - color_index_bits
        lsb_page_frame_index = int(math.log2(page_size))

        bitmask_raw = "X"*all_bits
        # mark all bits within page frame
        bitmask_raw = "-"*lsb_page_frame_index + bitmask_raw[lsb_page_frame_index:]
        # set color index
        bitmask_raw = bitmask_raw[0:lsb_color_index] + "00000" + bitmask_raw[msb_color_index:]

        print("bitmask_raw=" + bitmask_raw)
        print("bitmask_new=" + bitmask_raw[0:lsb_color_index] + format(5, '05b')[::-1] + bitmask_raw[msb_color_index:])

        color_cnt = 0
        for system_page_color, bitmask in mapping.items():
            b = bitmask_raw[0:lsb_color_index] + format(color_cnt, '05b')[::-1] + bitmask_raw[msb_color_index:]
            mapping[system_page_color] = b[::-1]
            color_cnt += 1

        return mapping

    color_addrspace_mapping = assign_address_spaces(system_page_colors)

    fmt1 = '{0: <17}'
    fmt2 = '{0: <10}'

    print_bar()
    print(fmt1.format('System Page Color')
          + ' : ' + fmt2.format('Address space(s)')
          )
    print_bar()

    for system_page_color, address_spaces in color_addrspace_mapping.items():
        print(fmt1.format(str(system_page_color))
              + ' : ' + fmt2.format(str(address_spaces))
              )

    print_bar()


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
            memory_consumer.reset_colors()

    @staticmethod
    def get_assignment_by_naive(hardware: Hardware, all_memory_consumers: Dict[str, MemoryConsumer]) -> \
            Dict[Hardware.SystemPageColor, Set[MemoryConsumer]]:

        assignment = {system_page_color: set() for system_page_color in hardware.get_all_system_page_colors()}

        num_assignable_colors = hardware.get_number_of_system_page_colors()
        num_required_colors = len(all_memory_consumers)
        all_system_page_colors = hardware.get_all_system_page_colors()

        if num_required_colors > num_assignable_colors:
            raise ColorAssigner.ColorExhaustion()
        else:
            for memory_consumer, color in zip(all_memory_consumers.values(), all_system_page_colors):
                assignment[color].add(memory_consumer)

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

    # TODO: review / deprecated?
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

        # get_colors is None or Empty for all memory consumers?
        assert all((not memory_consumer.get_colors()) for memory_consumer in all_memory_consumers.values()),\
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
                #if memory_consumer.get_color() is not None:
                if len(memory_consumer.get_colors()) == 1:
                    color_usage_counter_table[memory_consumer.get_colors()[0]] -= 1

                memory_consumer.add_color(assignable_color)
                color_usage_counter_table[assignable_color] += 1

                all_memory_consumers_values.remove(memory_consumer)

        # assign colors to rest of all_memory_consumers_values
        for memory_consumer in all_memory_consumers_values:
            assignable_color = get_next_assignable_color(color_usage_counter_table)
            memory_consumer.add_color(assignable_color)
            color_usage_counter_table[assignable_color] += 1

    # TODO: review / deprecated?
    @staticmethod
    def get_assignment_by_security_labels(hardware: Hardware, all_executors: Dict[str, Executor]) \
            -> Dict[MemoryConsumer, Set[Hardware.SystemPageColor]]:
        return {}

    # TODO: review / deprecated?
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
            cpu_access_constraints: Dict[Hardware.CPU, Set[Executor]] = None
    ) -> Dict[Hardware.SystemPageColor, Set[MemoryConsumer]]:
        # Check if all memory consumers are only assigned to one cache_isolation_domain
        # and initialize count value to zero
        #count_membership_of_mc: Dict[MemoryConsumer, int] = dict.fromkeys(all_memory_consumers.values(), 0)
        count_membership_of_mc = {memory_consumer: 0 for memory_consumer in all_memory_consumers.values()}
        for isolation_domain in cache_isolation_domains:
            for memory_consumer in isolation_domain:
                if memory_consumer in count_membership_of_mc.keys():
                    count_membership_of_mc[memory_consumer] += 1

        # logging.debug("count_membersip_of_mc" + str(count_membership_of_mc.items()))
        assert 0 not in count_membership_of_mc.values(), "All memory consumers of the system must be assigned at least " \
                                                         "to one cache isolation domain. #ASSMS-CACHE-ISOLATION-0"
        assert all(count == 1 for count in count_membership_of_mc.values()), "A memory consumer can only be member of" \
                                                                             " only one cache isolation domain. " \
                                                                             "#ASSMS-CACHE-ISOLATION-1"
        assert cpu_access_constraints is None, "CPU-Access-Constraints are currently unimplemented/not needed. " \
                                               "#ASSMS-CACHE-ISOLATION-7"

        # Algorithm idea:
        # Iterate through partitions and assign a pool of reservable colors to each cache isolation domain.
        #   We assign a pool of colors and not one color, because there can be several executors within the same
        #   cache isolation domain but which are not running on the same CPU core.
        #   So there is no single reservable color for {subject_X, subject_Y} when they're are running on different
        #   CPU cores.
        # After each iteration steps, the cache isolation domain members add all possible reservable colors to their own
        # colors.
        #   Possible means: System Page Colors' CPU part is CPU the memory consumer is accessed by (read/write/execute).
        # We repeat the iteration through cache isolation domains until there is no color to assign left.

        def assign_colors_to_cache_isolation_domain(cache_isolation_domain,
                                                    assignment: Dict[Hardware.SystemPageColor, Set[MemoryConsumer]]):
            """Assign colors to provided cache isolation domain"""
            def get_next_assignable_colors(
                    memory_consumer: MemoryConsumer,
                    assignment: Dict[Hardware.SystemPageColor, Set[MemoryConsumer]])\
                    -> List[Hardware.SystemPageColor]:
                """Returns the next assignable colors of a memory consumer without reserving them."""
                """
                Ideas:
                    - If MemoryConsumer is only on running one CPU cores (e. g. CPU_X), then just get the next free
                      (CPU_X, Y) page color.
                    - If MemoryConsumer is running on several CPU cores (e. g. CPU_X and CPU_Y), then get next free
                      colors (CPU_X, A) and (CPU_Y, B), where A == B.
                      Background:
                        Assuming MemoryConsumer is running on two CPU cores on one memory page. Then we must assume
                        that the MemoryConsumer can run with both CPU core on this memory page and occupying
                        two page colors for the same memory page.
                    - If a MemoryConsumer is a Channel then we could also need two page colors, if source and target
                      subjects are running on different CPU cores; if not, we only need one page color.
                """

                # get the CPU core(s) of the memory consumer and get next assignable SystemPageColors
                # with matching CPU core(s), which have all the same page_color, e. g.
                # (CPU_0, x), (CPU_1, y) when (CPU cores is CPU_0 and CPU_1) and where x=y.
                executors = memory_consumer.get_executors()
                cpus = []
                for executor in executors:
                    cpus.extend(executor_cpu_constraints[executor]) # TODO: bad style

                for cpu_page_color in range(hardware.get_number_of_cpu_page_colors()):
                    if all(len(assignment[Hardware.SystemPageColor(cpu, cpu_page_color)]) == 0 for cpu in cpus):
                        return [Hardware.SystemPageColor(cpu, cpu_page_color) for cpu in cpus]

                raise ColorAssigner.ColorExhaustion()

            def assign_colors(
                    cache_isolation_domain,
                    cache_isolation_domain_colors: List[Hardware.SystemPageColor],
                    assignment: Dict[Hardware.SystemPageColor, Set[MemoryConsumer]]
                    # color_table: Dict[Hardware.SystemPageColor, int]
            ):
                """Assign SystemPageColors to the MemoryConsumers in the cache isolation domain - if possible  -
                and mark the system page color as used in the color table."""
                for color in cache_isolation_domain_colors:
                    for memory_consumer in cache_isolation_domain:
                        executors = memory_consumer.get_executors() # TODO: bad style
                        memory_consumer_cpus = []
                        for executor in executors:
                            memory_consumer_cpus.extend(executor_cpu_constraints[executor])
                        # memory_consumer_cpus = [executor_cpu_constraints[executor] for executor in
                        #                        memory_consumer.get_executors()]
                        if color.get_cpu() in memory_consumer_cpus:
                            assignment[color].add(memory_consumer)
                            # memory_consumer.add_color(color)
                            # color_table[color] += 1

            cache_isolation_domain_colors: List[Hardware.SystemPageColor] = []

            for cache_isolation_member in cache_isolation_domain:
                colors = get_next_assignable_colors(cache_isolation_member, assignment)
                cache_isolation_domain_colors.extend(colors)

            assign_colors(cache_isolation_domain, cache_isolation_domain_colors, assignment)

            # colors assigned implies len(cache_isolation_domain_colors) > 0
            # logging.debug("cache_isolation_domain_colors:" + str(cache_isolation_domain_colors))
            return len(cache_isolation_domain_colors) > 0

        assignment = {system_page_color: set() for system_page_color in hardware.get_all_system_page_colors()}
        color_to_assign_available = True
        # counts how often a SystemPageColor is used
        # color_table = dict.fromkeys(hardware.get_all_system_page_colors(), 0)

        # while color_to_assign_available:
        #     color_to_assign_available = False
        #     for ci_domain in cache_isolation_domains:
        #         color_to_assign_available |= assign_colors_to_cache_isolation_domain(ci_domain, assignment)

        # only one iteration, TODO: more iteration until no color to assign left
        for ci_domain in cache_isolation_domains:
            color_to_assign_available |= assign_colors_to_cache_isolation_domain(ci_domain, assignment)

        return assignment

    @staticmethod
    def assign_by_cache_isolation_domains(
            hardware:                   Hardware,
            all_memory_consumers:       Dict[str, MemoryConsumer],
            cache_isolation_domains:    List[Set[MemoryConsumer]],
            executor_cpu_constraints:   Dict[Executor, Set[Hardware.CPU]] = None,
            cpu_access_constraints:     Dict[Hardware.CPU, Set[Executor]] = None
    ):
        """Assign colors by cache isolation domains method.

        A cache isolation domain contains a set of memory consumers and separates them (in the sense of cache
        non-interference) from other memory consumers of the system. That means that memory consumers of the same
        cache isolation domain reserve a set of colors which can be used by them and cannot be used by memory consumers
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
            - All memory consumers of the system must be assigned at least to one cache isolation domain.
              #ASSMS-CACHE-ISOLATION-0
            - A memory consumer can only be member of one cache isolation domain. #ASSMS-CACHE-ISOLATION-1
            # For simplicity commented out for now:
            #- If the cache isolation domain of a memory consumer is not explicitly specified by
            #  cache_isolation_domains,
            #  it is implicitly assumed that the memory consumer gets its own exclusive cache isolation domain.
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
            hardware: Hardware system.
            all_memory_consumers: All memory consumers of the hardware system.
            cache_isolation_domains: Cache isolation domains for which a valid page coloring is requested.
            executor_cpu_constraints: Executor-CPU-Constraints which must enforced on top of the cache isolation
                domains. See function documentation for details.
            cpu_access_constraints: (Currently not implemented/not needed) CPU-Access-Constraints which must enforced on
                top of the cache isolation domains. See function documentation for details.
        """
        assignment = ColorAssigner.get_assignment_by_cache_isolation_domains(
            hardware, all_memory_consumers, cache_isolation_domains, executor_cpu_constraints, cpu_access_constraints
        )
        ColorAssigner._enforce_assignment(assignment)

    @staticmethod
    def _enforce_assignment(assignment: Dict[Hardware.SystemPageColor, Set[MemoryConsumer]]):
        for color, memory_consumers in assignment.items():
            for memory_consumer in memory_consumers:
                # logging.debug("Add color: " + str(color))
                memory_consumer.add_color(color)
