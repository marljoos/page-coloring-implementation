#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import copy
import logging
import sys
from typing import List, Dict, Set, Tuple, Callable, FrozenSet, Union
from abc import ABC, abstractmethod

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

"""
This script models certain aspects of a page coloring algorithm which will be
integrated into a separation kernel (SK) build system.
"""


class System:
    """The system consists of all relevant information to infer page coloring information including hardware and
    software (MemoryConsumers, Subjects, Kernel)"""

    # Access to a page frame in physical memory will affect several cache sets of several cache levels.
    # These affected cache sets represent a cache colors for their cache.
    # This type should represent a type for such immutable cache sets, independently of a cache level.
    AffectedCacheSets = FrozenSet[int]
    # First list element, cache colors of L1 cache, second element, cache colors of L2 cache, ...
    AllCacheColors = List[Dict['System.AffectedCacheSets', 'Hardware.CacheColor']]
    PAGE_COLOR_TO_PAGE_ADDRESS_MAPPING_DEFAULT_PATH = "data/page_color_to_page_address_mapping_dump.pkl"

    def __init__(
            self,
            hardware: 'Hardware',
            memory_consumers: List['MemoryConsumer'],
            page_color_to_page_address_mapping_dump_file=None):

        self._hardware = hardware
        self._memory_consumers = memory_consumers

        self._cache_colors = self._construct_cache_colors(hardware)
        self._page_colors = self._construct_page_colors(hardware, self._cache_colors)

        self._page_color_to_page_address_mapping = None

        # If page-color-to-page-address-mapping-dump-file is given, try to load it.
        # If this fails recalculate page-co-or-to-page-address-mapping (This can take very long and should be done with
        # the Cython version for performance reasons
        if page_color_to_page_address_mapping_dump_file:
            self._page_color_to_page_address_mapping = \
                self._load_page_color_to_page_address_mapping(page_color_to_page_address_mapping_dump_file)

        if self._page_color_to_page_address_mapping is None:
            self._page_color_to_page_address_mapping = \
                self._construct_page_color_to_page_address_mapping(hardware, self._cache_colors)

        self._system_page_colors = self._construct_system_page_colors(hardware, self._page_colors)

    def get_all_memory_consumers(self):
        return self._memory_consumers

    def get_hardware(self):
        return self._hardware

    @staticmethod
    def _construct_cache_colors(hardware: 'Hardware') -> AllCacheColors:
        """Construct all cache colors of a hardware.

        Algorithm idea: Use minimal amount of page addresses/pages, and apply index function (See IndexFunction class)
        of all cacheline_capacity sized chunks of each page.
        """

        num_of_cache_levels: int = hardware.get_number_of_cache_levels()
        cache_colors: List[Dict[System.AffectedCacheSets, Hardware.CacheColor]] = \
            [{} for _ in range(num_of_cache_levels)]
        page_size = hardware.get_page_size()

        page_addresses = hardware.get_page_addresses()
        cache_of_level = hardware.get_cache_information()

        for level, cache_colors_current_level in enumerate(cache_colors, start=1):
            number_of_colors = cache_of_level[level - 1].get_number_of_colors()
            cacheline_capacity = cache_of_level[level - 1].get_cacheline_capacity()

            # Apply index function of cache to as many pages as number of colors of cache
            index_function = cache_of_level[level - 1].get_index_function()
            pages = list(page_addresses)[:number_of_colors]

            for i, page_address in enumerate(pages):
                affected_cache_sets_of_page = frozenset(list(map(
                    index_function,
                    range(page_address, page_address + page_size, cacheline_capacity)
                )))

                # Add CacheColor to dict
                cache_colors[level - 1][affected_cache_sets_of_page] = \
                    Hardware.CacheColor(name_prefix="L" + str(level), cache_sets=affected_cache_sets_of_page)

            assert(len(cache_colors[level - 1]) == number_of_colors),\
                "Not as many cache colors calculated as specified.\n"\
                "Cache level: " + str(level) + "\n"\
                "Calculated: " + str(len(cache_colors[level - 1])) + "\n"\
                "Expected: " + str(number_of_colors)

        return cache_colors

    def _construct_page_colors(self, hardware: 'Hardware', cache_colors: AllCacheColors):
        page_colors: List[Hardware.PageColor] = []
        num_of_cache_levels: int = hardware.get_number_of_cache_levels()
        cache_of_level = hardware.get_cache_information()
        page_size = hardware.get_page_size()
        page_addresses = hardware.get_page_addresses()
        # number of colors of last level cache (e. g. L3)
        number_of_colors = cache_of_level[num_of_cache_levels - 1].get_number_of_colors()
        pages = list(page_addresses)[:number_of_colors]

        for page_address in pages:
            all_cache_colors_of_page_color: List[Hardware.CacheColor] = []
            for i in range(num_of_cache_levels):
                index_function = cache_of_level[i].get_index_function()
                affected_cache_sets_of_page = frozenset(map(
                    index_function,
                    range(page_address, page_address + page_size, cache_of_level[i].get_cacheline_capacity())
                ))

                all_cache_colors_of_page_color.append(cache_colors[i][affected_cache_sets_of_page])

            page_colors.append(Hardware.PageColor(all_cache_colors_of_page_color))

        return page_colors

    @staticmethod
    def _load_page_color_to_page_address_mapping(page_color_to_page_address_mapping_dump_file)\
            -> Union[Dict['Hardware.PageColor', List[int]], None]:
        """Loads page color to page address mapping from file."""
        import pickle
        try:
            with open(page_color_to_page_address_mapping_dump_file, 'rb') as input:
                return pickle.load(input)
        except OSError:
            return None

    def _construct_page_color_to_page_address_mapping(self, hardware: 'Hardware', cache_colors: AllCacheColors):
        num_of_cache_levels: int = hardware.get_number_of_cache_levels()
        cache_of_level = hardware.get_cache_information()
        page_size = hardware.get_page_size()
        page_addresses = hardware.get_page_addresses()
        page_color_to_page_address_mapping = {page_color: [] for page_color in self._page_colors}

        logging.info("_construct_page_color_to_page_address_mapping: Construct PageColor to page address mapping ...")
        for page_address in page_addresses:
            all_cache_colors_of_page_color: List[Hardware.CacheColor] = []
            for i in range(num_of_cache_levels):
                index_function = cache_of_level[i].get_index_function()
                affected_cache_sets_of_page = frozenset(map(
                    index_function,
                    range(page_address, page_address + page_size, cache_of_level[i].get_cacheline_capacity())
                ))

                all_cache_colors_of_page_color.append(cache_colors[i][affected_cache_sets_of_page])

            page_color_to_page_address_mapping[Hardware.PageColor(all_cache_colors_of_page_color)].append(page_address)

        logging.info("_construct_page_color_to_page_address_mapping: Finished.")

        # Because constructing page color to page address mapping can take a lot of time
        # (especially for large address spaces) a backup of of the mapping is saved to disk and can be reused later.
        logging.info("_construct_page_color_to_page_address_mapping: Saving to file...")
        import pickle
        with open(self.PAGE_COLOR_TO_PAGE_ADDRESS_MAPPING_DEFAULT_PATH, 'wb') as output:
            pickle.dump(page_color_to_page_address_mapping, output, pickle.HIGHEST_PROTOCOL)
        logging.info("_construct_page_color_to_page_address_mapping: Finished.")

        return page_color_to_page_address_mapping

    @staticmethod
    def _construct_system_page_colors(hardware: 'Hardware', page_colors: List['Hardware.PageColors']):
        # TODO: Maybe add some validity checks. I've had a bug in here which computed wrong SystemPageColors.
        cpu_cores = hardware.get_cpu_cores()

        system_page_colors: List[Hardware.SystemPageColor] = []
        for page_color in page_colors:
            for cpu in cpu_cores:
                system_page_colors.append(Hardware.SystemPageColor(cpu, page_color))

        return system_page_colors

    def get_cache_colors(self):
        return self._cache_colors

    def get_page_colors(self):
        return self._page_colors

    def get_system_page_colors(self):
        return self._system_page_colors

    def get_page_color_to_page_address_mapping(self):
        return self._page_color_to_page_address_mapping


class Hardware:
    """Description of a hardware system which consists of CPU cores, main memory and (multiple layers) of caches."""

    class CPU:
        cpu_namespace = []
        cpu_ctr = 1

        def __init__(self, name: str = None):
            self.id = Hardware.CPU.cpu_ctr

            if name is None:  # if name is not specified, name is "CPU_$cpu_ctr"
                name = str(self.id)

            Hardware.CPU.cpu_ctr += 1

            assert name not in Hardware.CPU.cpu_namespace, "CPU core names must be unique."
            Hardware.CPU.cpu_namespace.append(name)
            self.name = name

        def __str__(self):
            return "CPU_" + self.name

        def __hash__(self):
            return hash(str(self))

        def __eq__(self, other):
            return isinstance(other, Hardware.CPU) and str(self) == str(other)

        def get_id(self):
            return self.id

    class CPUCacheConfig:
        """The CPU Cache configuration contains all relevant information about the relationship between the CPU cores
        of the system and the caches."""

        def __init__(self,
                     caches: List[List['Cache']],
                     cpu_cores: List['Hardware.CPU'],
                     cache_cpu_mappings: List[Set[Tuple['Cache', 'Hardware.CPU']]]
                     ):
            """
            Args:
                caches: List of list of caches, where the first element designates the list of L1 caches,
                the second element designates the list of L2 caches, etc.
                cpu_cores: List of CPU cores of the system.
                cache_cpu_mappings: List of mappings (in form of a set of tuples) from a cache to a CPU core.
                The first element designates the mappings of the L1 caches, the second element the mappings of the L2
                caches etc.
            """

            all_caches_of_all_levels = [cache for caches_of_one_level in caches for cache in caches_of_one_level]
            assert len(all_caches_of_all_levels) == len(set(all_caches_of_all_levels)), "All caches must be unique."
            assert len(cpu_cores) == len(set(cpu_cores)), "All CPU cores must be unique."
            assert len(caches) == len(cache_cpu_mappings),\
                "Number of cache levels (L1, L2, ...) is number of mappings (L1->CPU, L2->CPU, ...)."
            all_assigned_caches = \
                {cache for mapping in cache_cpu_mappings for cache, cpu in mapping}
            assert all((cache in all_assigned_caches) for cache in all_caches_of_all_levels),\
                "Each cache must be assigned to a CPU core."

            # We also assume that the caches of one cache level are structurally the same.
            # So it's forbidden to have one L1 cache which is flushed, while others are not flushed,
            # or one L2 cache which has a cacheline_capacity of 64, while another L2 cache has a different.
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

    class CacheColor:
        """
        A CacheColor is a cache set of a cache of a cache level which is affected as soon a a class of pages
        (page addresses) is accessed.
        """

        cache_color_ctr: Dict[str, int] = {}

        @classmethod
        def increase_and_get_cache_color_counter(cls, name_prefix: str):
            if name_prefix not in cls.cache_color_ctr:
                cls.cache_color_ctr[name_prefix] = 1
            else:
                cls.cache_color_ctr[name_prefix] += 1

            return cls.cache_color_ctr[name_prefix]

        def __init__(self, name_prefix: str, cache_sets: FrozenSet[int]):
            self.cache_sets = cache_sets
            self.name_prefix = name_prefix
            self.id = Hardware.CacheColor.increase_and_get_cache_color_counter(name_prefix)

        def get_cache_sets(self):
            return self.cache_sets

        def __str__(self):
            return "CC(" + self.name_prefix + "_" + str(self.id) + ")"

        def get_id(self):
            return str(self.id)

    class PageColor:
        """A PageColor is a list of CacheColors. The first list element refers to the CacheColor of the L1 cache,
        the second element to the CacheColor of the L2 cache, ..."""

        def __init__(self, cache_colors: List['Hardware.CacheColor']):
            self.cache_colors = cache_colors

        def __str__(self):
            return 'PC(' + str([str(cache_color) for cache_color in self.cache_colors]) + ')'

        def __hash__(self):
            return hash(str(self))

        def __eq__(self, other):
            # TODO: Review
            assert self.cache_colors == other.get_cache_colors()
            return isinstance(other, Hardware.PageColor) and str(self) == str(other)

        def get_cache_colors(self):
            return self.cache_colors

    class SystemPageColor:
        """A SystemPageColor consists of a CPU and a PageColor and can fully identify caches of all levels which are
        affected as soon as a CPU accesses a page.

        E. g. SystemPageColor SPC(CPU_2, PC(['CC(L1_1)', 'CC(L2_5)', 'CC(L3_85)']))
        refers to a SystemPageColor which is "touched" as soon as CPU_2 is accessing a page which results in
        affecting the PageColor with the CacheColors L1_1, L2_5 and L3_85. If e. g. L1 and L2 caches are CPU bound
        (that means CPUs have their own exclusive L1 and L2 cache), we can fully identify the physical caches touched
        (L1_1 of CPU_2, L2_5 of CPU_2).

        Note that not all SystemPageColors must be assigned resp. can be assigned under certain security circumstances.
        E. g. if Subject1 is only running on CPU_1, belongs to its own exclusive cache isolation domain
        (without others members) and gets the SystemPagecolor
        SPC(CPU_1, PC(['CC(L1_1)', 'CC(L2_5)', 'CC(L3_85)'])) assigned. Then no other MemoryConsumer may get
        SystemPageColor SPC(A, PC(['CC(L1_1)', 'CC(L2_5)', 'CC(L3_85)'])) for each A in (CPU_1, CPU_2, ...)
        because L3 may be a CPU shared cache and security-sensitive cache interference in CC(L3_85) would happen.
        """

        def __init__(self, cpu: 'Hardware.CPU', page_color: 'Hardware.PageColor'):
            self.cpu = cpu
            self.page_color = page_color

        def __str__(self):
            return "SPC(" + str(self.cpu) + ", " + str(self.page_color) + ")"

        def __hash__(self):
            return hash(str(self))

        def __eq__(self, other):
            return (isinstance(other, Hardware.SystemPageColor) and
                    self.cpu == other.get_cpu() and self.page_color == other.get_page_color())

        def get_cpu(self):
            return self.cpu

        def get_page_color(self):
            return self.page_color

    def __init__(self, cpu_cache_config: CPUCacheConfig, main_memory_size: int, address_bus_width: int,
                 page_size: int = 4096):
        """
        Args:
            address_bus_width:
            cpu_cache_config: Complex data structure which describes CPU cores, caches and their mappings to the
            CPU cores.
            page_size: Page size in bytes.
            main_memory_size: Main memory size in bytes.
        """
        assert main_memory_size % page_size == 0, "Main memory size must be dividable by page size."
        assert address_bus_width == 32 or address_bus_width == 64, "Only 32-bit or 64-bit address buses are supported."
        assert 2**address_bus_width > main_memory_size, "Given address bus width cannot handle given main memory size."

        self._cpu_cache_config = cpu_cache_config
        self._main_memory_size = main_memory_size
        self._page_size = page_size
        self._address_bus_width = address_bus_width

        self._page_addresses = range(0, self._main_memory_size, self._page_size)

    def get_page_size(self):
        return self._page_size

    def get_cpu_cores(self):
        return self._cpu_cache_config.get_cpu_cores()

    def get_cache_information(self) -> List['Cache']:
        """Returns a list of one cache of each cache level of the hardware, so that information about the caches can be
        obtained.

        This assumes, that all caches of a specific cache level deliver the same information see:
        #ASSMS-STRUCTURALLY-SAME-CACHES-ONE-SAME-LEVEL-1
        """

        cache_information: List[Cache] = []
        for caches_of_one_level in self._cpu_cache_config.get_caches():
            # TODO: Possibly bad style.
            cache_information.append(copy.deepcopy(caches_of_one_level[0]))

        return cache_information

    def get_page_addresses(self):
        return self._page_addresses

    def get_address_bus_width(self):
        return self._address_bus_width

    def get_number_of_cache_levels(self):
        return len(self._cpu_cache_config.get_caches())


class Cache:
    """Description of a CPU cache."""
    _cache_namespace = []
    _cache_ctr = 0

    # And index function maps a memory address to a unique numerical identifier of a Set of a Cache.
    IndexFunction = Callable[[int], int]

    @staticmethod
    def default_index_function(cacheline_capacity: int, number_of_sets: int) -> IndexFunction:
        from math import floor
        return lambda x: int(floor(x / cacheline_capacity)) % (number_of_sets)

    def __init__(self,
                 total_capacity: int,
                 associativity: int,
                 cacheline_capacity: int,
                 shared: bool = False,  # TODO: Documentation
                 flushed: bool = False,
                 page_size: int = 4096,
                 name_prefix: str = None,  # TODO: Documentation
                 index_function: IndexFunction = None  # TODO: Documentation
                 ):
        """
        Args:
            total_capacity: Total capacity of cache in bytes.
            associativity: Number of cache lines of a set in a cache.
            cacheline_capacity: Number of Bytes a cache line can store.
            flushed: True if cache is flushed on context/subject switch. This effectively enables the usage of
                colors of higher level caches.
            page_size: Page size in bytes.
        """

        if name_prefix is None:  # if name_prefix is not specified, name is "Cache_$(cache_ctr)_X"
            self._name = "Cache_" + str(Cache._cache_ctr) + "_X"
        else:  # else name is Cache_$(cache_ctr)_$(name_prefix)
            self._name = "Cache_" + str(Cache._cache_ctr) + "_" + name_prefix
        assert self._name not in Cache._cache_namespace, "Cache names must be unique."

        Cache._cache_ctr += 1
        Cache._cache_namespace.append(self._name)

        self._flushed = flushed
        self._shared = shared
        self._total_capacity = total_capacity
        self._associativity = associativity
        self._cacheline_capacity = cacheline_capacity
        self._sets = self._total_capacity / (self._associativity * self._cacheline_capacity)

        # The access of one page frame affects several sets of a cache.
        # The number of these affected sets depends not only on the page size
        # and the cache line capacity but also on the mapping of physical memory to cache lines.
        # We assume that the first $cacheline_capacity bytes of the page frame is allocated
        # to the first set of the cache, the second $cacheline_capacity bytes to
        # the second set etc. #ASSMS-CACHE-MAPPING
        self._affected_sets_per_page = page_size / self._cacheline_capacity

        # All by one page frame affected sets are assigned to one color.
        # We assume that a page frame owns the whole affected set even if it actually
        # uses only one cache line of it.
        # Depending on the replacement policy of the cache you in theory could use the
        # other cache lines for other colors as long other consumed cache lines aren't replaced.
        # So we assume a strict form of "coloring strategy" here. #ASSMS-COLORING-STRATEGY
        self._number_of_colors = self._sets / (page_size / self._cacheline_capacity)

        # We assume that all numbers defined here must be integer (no floats), otherwise there is something wrong
        # #ASSMS-CACHE-PROPS-ONLY-INTS
        assert (self._sets.is_integer()), "#ASSMS-CACHE-PROPS-ONLY-INTS"
        assert (self._affected_sets_per_page.is_integer()), "#ASSMS-CACHE-PROPS-ONLY-INTS"
        assert (self._number_of_colors.is_integer()), "#ASSMS-CACHE-PROPS-ONLY-INTS"
        self._sets = int(self._sets)
        self._affected_sets_per_page = int(self._affected_sets_per_page)
        self._number_of_colors = int(self._number_of_colors)

        if index_function:
            self._index_function = index_function
        else:
            self._index_function = Cache.default_index_function(
                cacheline_capacity=self._cacheline_capacity,
                number_of_sets=self._sets
            )

    def get_number_of_colors(self):
        return self._number_of_colors

    def get_flushed(self):
        return self._flushed

    def __str__(self):
        return self._name

    def get_number_of_sets(self):
        return self._sets

    def get_cacheline_capacity(self):
        return self._cacheline_capacity

    def get_index_function(self):
        return self._index_function

    def get_shared(self):
        return self._shared


class Executor:
    """Designates entities which are executed on the system (e. g. kernel, subjects)."""
    def __init__(self):
        pass


class MemoryConsumer:
    """A MemoryConsumer represents memory consuming objects like kernels, subjects or channels.

    A MemoryConsumer consumes certain memory of size $memsize > 0
    and may get assigned an address space of size $memsize and a color
    for this address space.
    A MemoryConsumer may also have a list of Executors which are accessing (read/write/execute) the memory region.
    """

    def __init__(self, name: str, memory_size: int, page_size: int = 4096):
        """
        Args:
            memory_size: Memory size of memory consumer in bytes.
            page_size: Page size in bytes.
        """

        assert memory_size % page_size == 0, "Memory size of memory consume must be a multiple of page size."
        assert memory_size > 0, "Memory size must be positive."

        self._name = name
        self._address_space = None
        self._memory_size = memory_size
        self._color = None
        self._executors: List[Executor] = []  # TODO: Documentation
        self._colors = []

    def get_name(self):
        return self._name

    def get_memory_size(self):
        return self._memory_size

    def reset_colors(self):
        self._colors = []

    def add_color(self, color: Hardware.SystemPageColor):
        self._colors.append(color)

    def get_colors(self):
        return self._colors

    def add_executor(self, executor: Executor):
        self._executors.append(executor)

    def get_executors(self):
        return self._executors

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
        assert __address_space_size(address_space) == self._memory_size,\
            "Size of specified address space must comply to the memory requirement/size of the MemoryConsumer."
        assert __address_space_not_overlapping(address_space),\
            "Address ranges must not be overlapping."

        self._address_space = address_space

    def get_address_space(self):
        return self._address_space


# We assume that Kernel memory pages can also be colored easily. #ASSMS-KERNEL-PAGE-COLORING
class Kernel(MemoryConsumer, Executor):
    def __init__(self, name, memory_size):
        super().__init__(name, memory_size)

        self.add_executor(self)


class Subject(MemoryConsumer, Executor):
    """A subject represents a running instance of a component on top of a SK.

    It has a memory requirement (in Byte) and may have channels to other subjects.
    """

    def __init__(self, name, memory_size):
        super().__init__(name, memory_size)

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
        """Returns all out channels to the given subject and all in channels from the given subject.

        Returns:
            List[Channel]: All out channels to given subject and all in channels from given subject.
        Raises: TODO: Raises exception if there is no in or out channel from/to subject.
        """
        return self.inchannels[subject] + self.outchannels[subject]


class Channel(MemoryConsumer):
    """A Channel represents an unidirectional communication relationship between
    a source subject and a target subject. A Channel has a memory requirement (in Byte).
    """

    def __init__(self, name: str, memory_size: int, source: Subject, target: Subject):
        super().__init__(name, memory_size)
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


class ColorAssigner(ABC):
    """Meta class responsible for assigning colors to MemoryConsumers."""

    class ColorAssignmentException(Exception):
        pass

    class ColorExhaustion(ColorAssignmentException):
        def __init__(self):
            default_message = "There are not enough colors to distribute. "\
                              "Maybe another color assignment method can help."
            super().__init__(default_message)

    @staticmethod
    def apply_assignment(assignment: Dict[Hardware.SystemPageColor, Set[MemoryConsumer]]):
        for color, memory_consumers in assignment.items():
            for memory_consumer in memory_consumers:
                # logging.debug("Add color: " + str(color))
                memory_consumer.add_color(color)

    @staticmethod
    def reset_colors(all_memory_consumers: Dict[str, MemoryConsumer]):
        for memory_consumer in all_memory_consumers.values():
            memory_consumer.reset_colors()

    @staticmethod
    @abstractmethod
    def get_assignment():
        pass


class IndexFunctionLibrary:
    @staticmethod
    def get_rose_level_3_index_function(
            L3_total_capacity, L3_cacheline_capacity, L3_associativity, address_bus_width)\
            -> Cache.IndexFunction:
        """
        L3 complex indexing function from Alexander Rose's internship report.
        """

        NUMBER_OF_SLICES = 4
        L3_number_of_sets = L3_total_capacity // (L3_associativity * L3_cacheline_capacity)
        L3_number_of_sets_per_slice = L3_number_of_sets // NUMBER_OF_SLICES

        # cache slice = cache block (complex indexing property of some Intel CPUs divides the cache into slices/blocks)
        def address_to_cache_slice_number(addr: int) -> int:
            # Binary representation of address
            addr_bin = format(addr, '0' + str(address_bus_width) + 'b')
            # Reverse so that Bit 0 is Array index 0 and convert to int for bit manipulation
            bit = [int(i) for i in reversed(addr_bin)]

            x_0 = bit[17] ^ bit[19] ^ bit[20] ^ bit[21] ^ bit[22] ^ bit[23] ^ bit[24] ^ bit[26] ^ bit[28] ^ bit[29] \
                  ^ bit[31] ^ bit[33] ^ bit[34]

            x_1 = bit[18] ^ bit[19] ^ bit[21] ^ bit[23] ^ bit[25] ^ bit[27] ^ bit[29] ^ bit[30] ^ bit[31] ^ bit[32] \
                  ^ bit[34]

            ret = (x_0 * 2 ** 0) + (x_1 * 2 ** 1)

            assert ret < NUMBER_OF_SLICES, "Slice number must be lower than the number of slices."

            return ret

        # Return cache set number within a block
        def address_to_cache_set_number(addr: int) -> int:
            from math import floor
            return floor(addr / L3_cacheline_capacity) % L3_number_of_sets_per_slice

        # Unique cache set identifier enumeration function maps:
        # (Slice number, Cache set number) -> (Slice number)*(Maximum sets) + Cache set number, e. g.
        # (0, 0) -> 0
        # (0, 1) -> 1
        # (0, L3_number_of_sets_per_slice - 1) = L3_number_of_sets_per_slice - 1
        # (1, 0) -> L3_number_of_sets_per_slice
        # (1, 1) -> L3_number_of_sets_per_slice + 1
        # ...
        # and finally the "last" cache set:
        # (3, L3_number_of_sets_per_slice -1) -> 3*L3_number_of_sets_per_slice + L3_number_of_sets_per_slice - 1

        return lambda addr: address_to_cache_slice_number(addr) * L3_number_of_sets + address_to_cache_set_number(addr)
