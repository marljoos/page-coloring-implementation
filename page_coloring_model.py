#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
from typing import List, Dict, Set  # need this for specifying List/Dict/Set types for type hints

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

"""
This script models certain aspects of a page-coloring algorithm which will be
integrated into a separation kernel (SK) build system.
"""

# Main memory size in Gibibyte
MAIN_MEMORY_SIZE = 4
# An address space is a list of allocated byte-addressing memory ranges
# which do not overlap
MAIN_MEMORY_ADDRESS_SPACE = [range(0, MAIN_MEMORY_SIZE * (1024 ** 3))]

# Page size in Byte
PAGE_SIZE = 4096

# Number of CPUs
NUM_CPUS = 4


class Cache:
    """Description of a CPU cache."""
    def __init__(self, total_capacity, associativity, cacheline_capacity, page_size=4096):
        """
        Args:
            total_capacity (int): Total capacity of cache in bytes.
            associativity (int): Number of cache lines of a set in a cache.
            cacheline_capacity (int): Number of Bytes a cache line can store.
            page_size (int): Page size in bytes.
        """
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
        # ASSMS-CACHE-PROPS-ONLY-INTS
        assert (self.sets.is_integer())
        assert (self.affected_sets_per_page.is_integer())
        assert (self.colors.is_integer())
        self.sets = int(self.sets)
        self.affected_sets_per_page = int(self.affected_sets_per_page)
        self.colors = int(self.colors)


class MemoryConsumer:
    # A MemoryConsumer represents an object like subjects or channels
    # which want to consume a certain memory of size $memsize > 0
    # and may get assigned an address space of size $memsize and a color
    # for this address space.

    def __init__(self, memsize, color=None):
        assert memsize % PAGE_SIZE == 0  # memory size of memory consume must be a multiple of page size
        assert memsize > 0

        self.memsize = memsize
        self.set_color(color)

    def set_color(self, color):
        self.color = color

    def get_color(self):
        return self.color

    def set_address_space(self, address_space: List[range]):
        assert len(address_space) > 0
        assert MemoryConsumer.__address_space_size(address_space) == self.memsize
        assert MemoryConsumer.__address_space_not_overlapping(address_space)

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


class Subject(MemoryConsumer):
    # A subject represents a running instance of a component on top of a SK.
    # It has a memory requirement (in Byte) and may have channels to other subjects.

    def __init__(self, memsize, channels=[]):
        super().__init__(memsize)
        self.channels = {}

    def getChannelTo(self, subject):
        return self.channels[subject]


class Channel(MemoryConsumer):
    # A channel represents an unidirectional communication relationship between
    # a source subject and a target subject and as well has a memory requirement (in Byte).

    def __init__(self, memsize, source: Subject, target: Subject):
        super().__init__(memsize)
        self.source = source
        self.target = target


###############################################################################

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
        logging.debug('used_colors_table: ' + str(used_colors_table))

    logging.info('Number of used colors: ' + str(color_ctr))


def print_memory_consumer_colors(all_memory_consumers: Dict[str, MemoryConsumer]) -> None:
    fmt = '{0: <20}'  # format string with width 20
    print(fmt.format('Memory Consumer') + ': Color')
    print("=" * 30)
    for name, memory_consumer in all_memory_consumers.items():
        print(fmt.format(name) + ": " + str(memory_consumer.get_color()))


###############################################################################

def main():
    # Specification of subjects and their memory requirements.
    subjects = {
        'Untrusted App 1': Subject(2 * PAGE_SIZE),
        'Linux': Subject(4 * PAGE_SIZE),
        'Crypto': Subject(8 * PAGE_SIZE),
        'Trusted Subject': Subject(10 * PAGE_SIZE),
        'Trusted App 2': Subject(11 * PAGE_SIZE)
    }

    # Specification of allowed unidirectional communcation relationships (channels)
    # between two subjects and the memory requirement of the channel.
    channels = {
        'UApp to TApp': Channel(6 * PAGE_SIZE, subjects['Untrusted App 1'], subjects['Trusted App 2']),
        'TApp to UApp': Channel(1 * PAGE_SIZE, subjects['Trusted App 2'], subjects['Untrusted App 1'])
    }

    all_memory_consumers = {**subjects, **channels}

    # Specification of interference domains.
    # An interference domain is a set of memory consumers whose memory regions are allowed to
    # interfere with each others in cache(s). 
    # Interference domains effectively lead to less color usage
    # since members of the same interference domain may share the same color.
    interference_domains = [
        {subjects['Untrusted App 1'], subjects['Linux']},
        {subjects['Crypto']},
        {subjects['Trusted Subject']},
        {channels['UApp to TApp'], channels['TApp to UApp']}
    ]

    # TODO: Description of cpu_execution_domain.
    # TODO: Use System instead of one single L3 cache
    l3cache = Cache(total_capacity=6 * (1024 ** 2), associativity=12, cacheline_capacity=64)

    assign_memory_consumer_colors(all_memory_consumers, interference_domains, l3cache, minimize_colors=True)

    print_memory_consumer_colors(all_memory_consumers)

    # DONE 1: must somehow model shared memory (channels)
    # TODO 2: assign_memory_consumer_colors is too naive, list of interference domains don't have to be disjunct.
    # TODO 3: State assumptions. Split L1 instruction cache & L1 data cache, complex indexing.
    # TODO 4: Take care of reserved memory.
    # TODO 5: Noch einmal über interference domains nachdenken. Wenn sich Subjekt 1 und Subjekt 2 gegenseitig stören
    #         dürfen, dann gilt das implizit auch für ihre Channels untereinander.
    #         Ggf. einfach eine Warning ausgeben, dass Farben gespart werden könnten, statt implizit die Channels in
    #         die gleiche interference domain zuzuordnen.
    # TODO 6: Take care of CPUs and CPU specific cache.


if __name__ == "__main__":
    main()
