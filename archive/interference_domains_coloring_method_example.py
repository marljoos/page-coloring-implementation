#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from page_coloring_model import *
from itertools import cycle
import logging


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

    logging.info("Number of usable colors per CPU (CPU page color): " + str(hardware.get_number_of_cpu_page_colors()))
    logging.info("Number of all system page colors: " + str(hardware.get_number_of_system_page_colors()))

    # DEBUG: Print all system page colors.
    logging.info("System page colors:")
    for system_page_color in hardware.get_all_system_page_colors():
        logging.info(system_page_color)

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
            Channel(2 * PAGE_SIZE, subjects['Untrusted App'], subjects['Untrusted Linux Public'])
    }

    all_memory_consumers = {'Kernel': kernel, **subjects, **channels}

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

    logging.info("Color assignment (with interference domains method):")
    ColorAssigner.reset_colors(all_memory_consumers)
    ColorAssigner.assign_color_by_interference_domains(hardware, all_memory_consumers, interference_domains)
    print_memory_consumer(all_memory_consumers)


if __name__ == "__main__":
    main()
