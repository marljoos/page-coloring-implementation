#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
from typing import List, Dict, Set, Tuple  # need this for specifying List/Dict/Set types for type hints
from itertools import cycle

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
                caches: List of list of caches, where the first elements designates the list of L1 caches,
                the second elements, designates the list of L2 caches, etc.
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


class Executable:
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
class Kernel(MemoryConsumer, Executable):
    pass


class Subject(MemoryConsumer, Executable):
    """A subject represents a running instance of a component on top of a SK.

    It has a memory requirement (in Byte) and may have channels to other subjects."""

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
        """Returns all in and out channels of this s

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


def assign_memory_consumer_colors(
        all_memory_consumers: Dict[str, MemoryConsumer],
        interference_domains: List[Set[MemoryConsumer]],
        cache,
        minimize_colors=False):
    # Precondition 1: The sets in interference_domains must not be pairwise subsets of
    #                 each other. Otherwise the color counter may yield an incorrect value.
    #                 #ASSMS-INTERFERENCE-DOMAINS
    #                 Example:
    #                   - [ { subj1, subj2 }, { subj1, subj2, subj3 } ] is not allowed.
    #                     Color counter would result in color-counter = 2 instead of color-counter = 1 of all subjects.
    #                   - [ { subj1, subj2 }, { subj2, subj3 } ] is allowed.
    #                     Must result in 2 colors. E. g. color 1 to subj1, color 2 to { subj2, subj3 }.
    #                 TODO: Überarbeiten, funktioniert nicht mit
    #                       [ { subj1, subj2 }, { subj2, subj3 } , { subj1, subj3 } ]
    #                       würde aktuell zu 2 genutzten Farben führen, obwohl der color counter 3 ist.
    #                       subj1.color = subj2.color = 1, subj2.color = subj3.color = 2, subj1.color = subj3.color = 3,
    #                       genutzte Farben = { 2,3 }
    # Idea:
    # 1. Get number of all assignable colors (dependent on cache)
    # 2. Get upper bound of required colors (len(all_memory_consumers))
    # 3. If len(all_memory_consumers) < all_assignable colors and not MINIMIZE_COLORS:
    #       assign colors incrementally
    #    else:
    #       1. iterate through interference domains
    #           1. assign same color to memory consumers in same interference domain
    #              (if a memory consumer was colored before, it's color gets overwritten)
    #           2. remove colored memory consumers from all_memory_consumers
    #           3. increase assigned_color_counter to later assure
    #              it is small than the number of all assignable colors
    #           4. If assigned_color_counter >= number of all assignable colors
    #              return EXCEPTION (color exhaustion)
    #       2. assign rest of colors incrementally to rest of all_memory_consumers and
    #          assure that there is no color exhaustion

    num_assignable_colors = cache.colors
    num_max_required_colors = len(all_memory_consumers)

    color_ctr = 0

    # CAUTION: This assumes that all memory consumer colors are undefined before. #ASSMS-UNDEFINED-COLORS
    if num_max_required_colors <= num_assignable_colors and not minimize_colors:
        for memory_consumer in all_memory_consumers.values():
            memory_consumer.set_color(color_ctr)
            color_ctr += 1
    else:
        all_memory_consumers_values = list(all_memory_consumers.values())
        used_colors_table = [0 for i in range(0, num_assignable_colors)]

        for interference_domain in interference_domains:
            assignable_color = used_colors_table.index(0)  # get lowest color which is unallocated (with 0 uses)
            for memory_consumer in interference_domain:
                if memory_consumer.get_color() is not None:
                    used_colors_table[memory_consumer.get_color()] -= 1
                memory_consumer.set_color(assignable_color)
                used_colors_table[assignable_color] += 1

                all_memory_consumers_values.remove(memory_consumer)

        # assign colors to rest of all_memory_consumers_values
        for memory_consumer in all_memory_consumers_values:
            assignable_color = used_colors_table.index(0)
            # we assume that colors are undefined see #ASSMS-UNDEFINED-COLORS
            assert (memory_consumer.get_color() is None)
            memory_consumer.set_color(assignable_color)
            used_colors_table[assignable_color] += 1

        # count colors which are used (> 0)
        color_ctr = sum(color > 0 for color in used_colors_table)

    logging.info('Number of used colors: ' + str(color_ctr))



###############################################################################


def main():
    # Main memory size in Gibibyte
    MAIN_MEMORY_SIZE = 4
    # An address space is a list of allocated byte-addressing memory ranges
    # which do not overlap
    MAIN_MEMORY_ADDRESS_SPACE = [range(0, MAIN_MEMORY_SIZE * (1024 ** 3))]

    # Page size in Byte
    PAGE_SIZE = 4096

    # Number of CPU cores
    NUM_CPUS = 4

    cpu_cores = [Hardware.CPU() for _ in range(0, NUM_CPUS)]
    l1_caches = \
        [Cache(total_capacity=(32 * 1024), associativity=8, cacheline_capacity=64, flushed=True, page_size=PAGE_SIZE)
         for _ in range(0, len(cpu_cores))]
    l2_caches = \
        [Cache(total_capacity=(256 * 1024), associativity=8, cacheline_capacity=64, page_size=PAGE_SIZE)
         for _ in range(0, len(cpu_cores)//2)]
    l3_caches = [Cache(total_capacity=6 * (1024 ** 2), associativity=12, cacheline_capacity=64, page_size=PAGE_SIZE)]

    logging.info('Number of L1 colors: ' + str(l1_caches[0].get_colors()))
    logging.info('Number of L2 colors: ' + str(l2_caches[0].get_colors()))
    logging.info('Number of L3 colors: ' + str(l3_caches[0].get_colors()))

    assert(len(l2_caches) == 2), "#ASSMS-CACHE-CONFIG-1"
    assert(len(l3_caches) == 1), "#ASSMS-CACHE-CONFIG-2"

    cpu_cache_config = Hardware.CPUCacheConfig(
        caches=[l1_caches, l2_caches, l3_caches],
        cpu_cores=cpu_cores,
        cache_cpu_mappings=[  # 1st element -> L1 cache mappings, 2nd element -> L2 cache mappings, etc.
            # one dedicated L1 cache per CPU core
            {l1_cache: cpu for (cpu, l1_cache) in zip(cpu_cores, l1_caches)},
            # assumes two L2 caches #ASSMS-CACHE-CONFIG-1
            {l2_cache: cpu for (cpu, l2_cache)
             in zip(cpu_cores, [l2_caches[0], l2_caches[0], l2_caches[1], l2_caches[1]])},
            # every CPU core gets the same L3 cache
            # assumes one L3 cache for all CPU cores #ASSMS-CACHE-CONFIG-2
            {l3_cache: cpu for (cpu, l3_cache) in zip(cpu_cores, cycle(l3_caches))}
        ]
    )

    hardware = Hardware(cpu_cache_config=cpu_cache_config, page_size=PAGE_SIZE)


    # We specify an example system which not only consists of its hardware
    # but also of its memory consumers which either reserve a specific address range or have a
    # memory size requirement specified in bytes.
    # Memory consumers are the Kernel, Subjects, Channels and also some special reserved address spaces.
    # The software of our example system consists on the one hand of the Kernel, an App and a Crypto subject which
    # all three are considered trusted and on the other hand several of untrusted Linux subjects.
    # To make it more realistic, there are for channels which connects some of the subjects to each other as shown here:
    # [some_reserved_address_space] | (Kernel) | (Trusted App) <-> (Trusted Crypto) <-> (Untrusted Linux VS-Vertr)
    #                                                              (Trusted Crypto) <-> (Untrusted Linux VS-NfD-1)
    #                                                              (Trusted Crypto) <-> (Untrusted Linux VS-NfD-2)
    #                                                              (Trusted Crypto) <-> (Untrusted Linux Public)
    #                                                      (Untrusted Linux Public) <-> (Untrusted App)
    # TODO: model potentially reserved address space as MemoryConsumer

    kernel = Kernel(16 * PAGE_SIZE)

    # Specification of subjects and their memory requirements.
    subjects = {
        'Trusted App':                Subject(2 * PAGE_SIZE),
        'Trusted Crypto':             Subject(4 * PAGE_SIZE),
        'Untrusted Linux VS-Vertr':   Subject(8 * PAGE_SIZE),
        'Untrusted Linux VS-NfD-1':   Subject(8 * PAGE_SIZE),
        'Untrusted Linux VS-NfD-2':   Subject(8 * PAGE_SIZE),
        'Untrusted Linux Public':     Subject(8 * PAGE_SIZE),
        'Untrusted App':              Subject(8 * PAGE_SIZE),
    }

    # Specification of allowed unidirectional communication relationships (channels)
    # between two subjects and the memory requirement of the channel.
    channels = {
        'Trusted App -> Trusted Crypto': Channel(6 * PAGE_SIZE, subjects['Trusted App'], subjects['Trusted Crypto']),
        'Trusted App <- Trusted Crypto': Channel(6 * PAGE_SIZE, subjects['Trusted Crypto'], subjects['Trusted App']),
        ##
        'Trusted Crypto -> Untrusted Linux VS-Vertr':
            Channel(6 * PAGE_SIZE, subjects['Trusted Crypto'], subjects['Untrusted Linux VS-Vertr']),
        'Trusted Crypto <- Untrusted Linux VS-Vertr':
            Channel(6 * PAGE_SIZE, subjects['Untrusted Linux VS-Vertr'], subjects['Trusted Crypto']),
        ##
        'Trusted Crypto -> Untrusted Linux VS-NfD-1':
            Channel(6 * PAGE_SIZE, subjects['Trusted Crypto'], subjects['Untrusted Linux VS-NfD-1']),
        'Trusted Crypto <- Untrusted Linux VS-NfD-1':
            Channel(6 * PAGE_SIZE, subjects['Untrusted Linux VS-NfD-1'], subjects['Trusted Crypto']),
        ##
        'Trusted Crypto -> Untrusted Linux VS-NfD-2':
            Channel(6 * PAGE_SIZE, subjects['Trusted Crypto'], subjects['Untrusted Linux VS-NfD-2']),
        'Trusted Crypto <- Untrusted Linux VS-NfD-2':
            Channel(6 * PAGE_SIZE, subjects['Untrusted Linux VS-NfD-2'], subjects['Trusted Crypto']),
        ##
        'Trusted Crypto -> Untrusted Linux Public':
            Channel(6 * PAGE_SIZE, subjects['Trusted Crypto'], subjects['Untrusted Linux Public']),
        'Trusted Crypto <- Untrusted Linux Public':
            Channel(6 * PAGE_SIZE, subjects['Untrusted Linux Public'], subjects['Trusted Crypto']),
        ##
        'Untrusted Linux Public -> Untrusted App':
            Channel(2 * PAGE_SIZE, subjects['Untrusted Linux Public'], subjects['Untrusted App']),
        'Untrusted Linux Public <- Untrusted App':
            Channel(2 * PAGE_SIZE, subjects['Untrusted Linux Public'], subjects['Untrusted App']),
    }

    all_memory_consumers = {'Kernel': kernel, **subjects, **channels}

    # BEGIN: Interference domains specification
    # Example usage of the interference domains method.
    # An interference domain is a set of memory consumers whose memory regions are allowed to
    # interfere with each others in cache(s). 
    # Interference domains effectively lead to less color usage
    # since members of the same interference domain may share the same color.
    # Non specified memory consumers get exclusive colors.
    interference_domains = [
       {  # All untrusted subjects and their channels may share the same color
        subjects['Untrusted Linux Public'],
        subjects['Untrusted App'],
        *subjects['Untrusted Linux Public'].get_channels(),
        *subjects['Untrusted App'].get_channels()
        },
       {  # The address space of the kernel and the trusted subjects may share the same color
        subjects['Trusted App'], subjects['Trusted Crypto'], kernel
       }
    ]

    # END: Interference domains specification

    # BEGIN: Security clearance specification
    # Example usage of the security labels method.
    # Building a security clearance hierarchy like this:
    #           Kernel
    #           /    \
    # Trusted App | Trusted Crypto
    #           \    /
    #       Linux VS-Vertr
    #           /    \
    #   L VS-NfD-1 | L VS-NfD-1
    #           \    /
    # { Linux Public, Untrusted App }
    #
    # Properties:
    #  - No cache-interference with upper classifications (e. g. Trusted App to Kernel)
    #  - No cache-interference with other compartments/partitions (e. g. Trusted App to Trusted Crypto)

    class C12n:  # Classification
        TOP_LEVEL, LEVEL_2, LEVEL_3, LEVEL_4, LEVEL_5 = range(0, 5)

    class Partition:
        ONE, TWO = range(0, 2)

    s = subjects

    kernel.                         set_security_label(C12n.TOP_LEVEL,  {Partition.ONE, Partition.TWO})
    s['Trusted App'].               set_security_label(C12n.LEVEL_2,    {Partition.ONE})
    s['Trusted Crypto'].            set_security_label(C12n.LEVEL_2,    {Partition.TWO})
    s['Untrusted Linux VS-Vertr'].  set_security_label(C12n.LEVEL_3,    {Partition.ONE, Partition.TWO})
    s['Untrusted Linux VS-NfD-1'].  set_security_label(C12n.LEVEL_4,    {Partition.ONE})
    s['Untrusted Linux VS-NfD-2'].  set_security_label(C12n.LEVEL_4,    {Partition.TWO})
    s['Untrusted Linux Public'].    set_security_label(C12n.LEVEL_5,    set())
    s['Untrusted App'].             set_security_label(C12n.LEVEL_5,    set())

    # END: Security clearance specification

    logging.info("Color assignment (naive method):")
    ColorAssigner.assign_colors_by_naive(hardware=hardware, all_memory_consumers=all_memory_consumers)
    # TODO: Use System instead of one single L3 cache
    l3cache = Cache(total_capacity=6 * (1024 ** 2), associativity=12, cacheline_capacity=64)

    assign_memory_consumer_colors(all_memory_consumers, interference_domains, l3cache, minimize_colors=True)

    print_memory_consumer(all_memory_consumers)

    # DONE 1: must somehow model shared memory (channels)
    # DONE 2: assign_memory_consumer_colors is too naive, list of interference domains don't have to be disjoint.
    # NOT DONE 3: State assumptions. Split L1 instruction cache & L1 data cache, complex indexing.
    # TODO 4: Take care of reserved memory.
    # TODO 5: Noch einmal über interference domains nachdenken. Wenn sich Subjekt 1 und Subjekt 2 gegenseitig stören
    #         dürfen, dann gilt das implizit auch für ihre Channels untereinander.
    #         Ggf. einfach eine Warning ausgeben, dass Farben gespart werden könnten, statt implizit die Channels in
    #         die gleiche interference domain zuzuordnen.
    # TODO 6: Take care of CPUs.
    # TODO 7: Take care of several level of caches (L2, L1).
    # TODO 8: Take care of CPU specific caches (L1 data & instruction cache).
    # TODO 9: Take care of complex indexing in L3 cache.


if __name__ == "__main__":
    main()
