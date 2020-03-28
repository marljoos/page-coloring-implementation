#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from page_coloring_model import *
from page_coloring_model_pretty_printer import PageColoringModelPrettyPrinter
from asp_color_assigner import ASPColorAssigner

import itertools
import logging


def main():
    # Main memory size in Gibibyte
    MAIN_MEMORY_SIZE_GB = 4  # TODO: add MAIN_MEMORY_SIZE as System/Hardware class attribute
    logging.info('Main memory size (Gibibyte): ' + str(MAIN_MEMORY_SIZE_GB))

    # Size of a memory address in bits
    ADDRESS_BUS_WIDTH = 64
    logging.info('Address bus width: ' + str(ADDRESS_BUS_WIDTH))

    # Page size in Byte
    PAGE_SIZE = 4096
    logging.info('Page size: ' + str(PAGE_SIZE))

    # Number of CPU cores
    NUM_CPUS = 4
    logging.info('Number of CPU cores: ' + str(NUM_CPUS))
    PageColoringModelPrettyPrinter.print_bar()

    cpu_cores = [Hardware.CPU() for _ in range(0, NUM_CPUS)]
    # TODO: Maybe implement "CacheList" type to ensure one level of caches only has structurally equal caches.
    l1_caches = \
        [Cache(total_capacity=(32 * 1024), associativity=8, cacheline_capacity=64, shared=False, flushed=True,
               page_size=PAGE_SIZE, name_prefix="L1")
         for _ in range(0, len(cpu_cores))]
    l2_caches = \
        [Cache(total_capacity=(256 * 1024), associativity=8, cacheline_capacity=64, shared=False, flushed=False,
               page_size=PAGE_SIZE, name_prefix="L2")
         for _ in range(0, len(cpu_cores))]

    L3_TOTAL_CAPACITY=6 * (1024 ** 2)
    L3_ASSOC=12
    L3_CACHELINE_CAPACITY=64

    l3_caches = [Cache(
                    total_capacity=6 * (1024 ** 2),
                    associativity=12,
                    cacheline_capacity=64,
                    shared=True,
                    flushed=False,
                    page_size=PAGE_SIZE,
                    name_prefix="L3",
                    index_function=IndexFunctionLibrary.get_rose_level_3_index_function(
                        L3_TOTAL_CAPACITY, L3_CACHELINE_CAPACITY, L3_ASSOC, ADDRESS_BUS_WIDTH
                    ))
    ]

    logging.info('L1 cache(s):')
    PageColoringModelPrettyPrinter.print_cache(l1_caches[0])
    logging.info('L2 cache(s):')
    PageColoringModelPrettyPrinter.print_cache(l2_caches[0])
    logging.info('L3 cache(s):')
    PageColoringModelPrettyPrinter.print_cache(l3_caches[0])

    assert(len(l3_caches) == 1), "#ASSMS-CACHE-CONFIG-2"

    cpu_cache_config = Hardware.CPUCacheConfig(
        caches=[l1_caches, l2_caches, l3_caches],
        cpu_cores=cpu_cores,
        cache_cpu_mappings=[  # 1st element -> L1 cache mappings, 2nd element -> L2 cache mappings, etc.
            # one dedicated L1 cache per CPU core
            {(l1_cache, cpu) for (cpu, l1_cache) in zip(cpu_cores, l1_caches)},
            {(l2_cache, cpu) for (cpu, l2_cache) in zip(cpu_cores, l2_caches)},
            # every CPU core gets the same L3 cache
            # assumes one L3 cache for all CPU cores #ASSMS-CACHE-CONFIG-2
            {(l3_cache, cpu) for (cpu, l3_cache) in zip(cpu_cores, itertools.cycle(l3_caches))}
        ]
    )

    logging.info("CPU cache configuration:")
    PageColoringModelPrettyPrinter.print_cpu_cache_config(cpu_cache_config)

    hardware = Hardware(cpu_cache_config=cpu_cache_config, main_memory_size=MAIN_MEMORY_SIZE_GB * (1024 ** 3),
                        address_bus_width=ADDRESS_BUS_WIDTH, page_size=PAGE_SIZE)

    # TODO: To be reviewed. Do we still need get_number_of_cpu_page_colors?
    # logging.info("Number of usable colors per CPU (CPU page color): " + str(hardware.get_number_of_cpu_page_colors()))
    # TODO: To be reviewed. Do we still need get_number_of_system_page_colors?
    # logging.info("Number of all system page colors: " + str(hardware.get_number_of_system_page_colors()))

    # logging.info("System page colors:")
    # # TODO: Replace with simpler PrettyPrinter function
    # for system_page_color in hardware.get_all_system_page_colors():
    #     print(system_page_color, end=' ')
    # print("")
    # PrettyPrinter.print_bar()

    logging.info(
        "Modelling the following system:\n"
        "(Kernel) | (Trusted App) <-> (Trusted Crypto) <-> (Untrusted Linux VS-Vertr)\n"
        "                             (Trusted Crypto) <-> (Untrusted Linux VS-NfD-1)\n"
        "                             (Trusted Crypto) <-> (Untrusted Linux VS-NfD-2)\n"
        "                             (Trusted Crypto) <-> (Untrusted Linux Public)\n"
        "                     (Untrusted Linux Public) <-> (Untrusted App)"
    )
    PageColoringModelPrettyPrinter.print_bar()

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
    # TODO: model potentially reserved address space as MemoryRegion

    # Specification of executors and their memory requirements.
    executors = {
        'Kernel':           Kernel('Muen SK', 16 * PAGE_SIZE),
        'T_APP':            Subject('Trusted App', 3 * PAGE_SIZE),
        'T_CRYPTO':         Subject('Trusted Crypto', 3 * PAGE_SIZE),
        'U_Linux_VS_V':     Subject('Untrusted Linux VS-Vertr', 8 * PAGE_SIZE),
        'U_Linux_VS_NfD_1': Subject('Untrusted Linux VS-NfD-1', 1 * 8193 * PAGE_SIZE),
        'U_Linux_VS_NfD_2': Subject('Untrusted Linux VS-NfD-2', 8 * PAGE_SIZE),
        'U_Linux_Public':   Subject('Untrusted Linux Public', 8 * PAGE_SIZE),
        'U_App':            Subject('Untrusted App', 8 * PAGE_SIZE)
    }

    e = executors

    # Specification of allowed unidirectional communication relationships (channels)
    # between two subjects and the memory requirement of the channel.
    channels2 = {
        'TA_2_TC':           Channel(
                                name='Trusted App -> Trusted Crypto',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['T_APP'],
                                readers=[e['T_CRYPTO']]),
        'TC_2_TA':            Channel(
                                name='Trusted App <- Trusted Crypto',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['T_CRYPTO'],
                                readers=[e['T_APP']]),
        ##
        'TC_2_UVertr':         Channel(
                                name='Trusted Crypto -> Untrusted Linux VS-Vertr',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['T_CRYPTO'],
                                readers=[e['U_Linux_VS_V']]),
        'UVertr_2_TC':       Channel(
                                name='Trusted Crypto <- Untrusted Linux VS-Vertr',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['U_Linux_VS_V'],
                                readers=[e['T_CRYPTO']]),
        ##
        'TC_2_UNFD1':       Channel(
                                name='Trusted Crypto -> Untrusted Linux VS-NfD-1',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['T_CRYPTO'],
                                readers=[e['U_Linux_VS_NfD_1']]),
        'UNFD1_2_TC':       Channel(
                                name='Trusted Crypto <- Untrusted Linux VS-NfD-1',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['U_Linux_VS_NfD_1'],
                                readers=[e['T_CRYPTO']]),
        ##
        'TC_2_UNFD2':       Channel(
                                name='Trusted Crypto -> Untrusted Linux VS-NfD-2',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['T_CRYPTO'],
                                readers=[e['U_Linux_VS_NfD_2']]),
        'UNFD2_2_TC':       Channel(
                                name='Trusted Crypto <- Untrusted Linux VS-NfD-2',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['U_Linux_VS_NfD_2'],
                                readers=[e['T_CRYPTO']]),
        ##
        'TC_2_UPUB':        Channel(
                                name='Trusted Crypto -> Untrusted Linux Public',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['T_CRYPTO'],
                                readers=[e['U_Linux_Public']]),
        'UPUB_2_TC':        Channel(
                                name='Trusted Crypto <- Untrusted Linux Public',
                                memory_size=6 * PAGE_SIZE,
                                writer=e['U_Linux_Public'],
                                readers=[e['T_CRYPTO']]),
        ##
        'UPUB_2_UA':       Channel(
                                name='Untrusted Linux Public -> Untrusted App',
                                memory_size=2 * PAGE_SIZE,
                                writer=e['U_Linux_Public'],
                                readers=[e['U_App']]),
        'UA_2_UPUB':       Channel(
                                name='Untrusted Linux Public <- Untrusted App',
                                memory_size=2 * PAGE_SIZE,
                                writer=e['U_App'],
                                readers=[e['U_Linux_Public']])
    }
    channels = [
        Channel(
            name='Trusted App -> Trusted Crypto',
            memory_size=6 * PAGE_SIZE,
            writer=e['T_APP'],
            readers=[e['T_CRYPTO']]),
        Channel(
            name='Trusted App <- Trusted Crypto',
            memory_size=6 * PAGE_SIZE,
            writer=e['T_CRYPTO'],
            readers=[e['T_APP']]),
        ##
        Channel(
            name='Trusted Crypto -> Untrusted Linux VS-Vertr',
            memory_size=6 * PAGE_SIZE,
            writer=e['T_CRYPTO'],
            readers=[e['U_Linux_VS_V']]),
        Channel(
            name='Trusted Crypto <- Untrusted Linux VS-Vertr',
            memory_size=6 * PAGE_SIZE,
            writer=e['U_Linux_VS_V'],
            readers=[e['T_CRYPTO']]),
        ##
        Channel(
            name='Trusted Crypto -> Untrusted Linux VS-NfD-1',
            memory_size=6 * PAGE_SIZE,
            writer=e['T_CRYPTO'],
            readers=[e['U_Linux_VS_NfD_1']]),
        Channel(
            name='Trusted Crypto <- Untrusted Linux VS-NfD-1',
            memory_size=6 * PAGE_SIZE,
            writer=e['U_Linux_VS_NfD_1'],
            readers=[e['T_CRYPTO']]),
        ##
        Channel(
            name='Trusted Crypto -> Untrusted Linux VS-NfD-2',
            memory_size=6 * PAGE_SIZE,
            writer=e['T_CRYPTO'],
            readers=[e['U_Linux_VS_NfD_2']]),
        Channel(
            name='Trusted Crypto <- Untrusted Linux VS-NfD-2',
            memory_size=6 * PAGE_SIZE,
            writer=e['U_Linux_VS_NfD_2'],
            readers=[e['T_CRYPTO']]),
        ##
        Channel(
            name='Trusted Crypto -> Untrusted Linux Public',
            memory_size=6 * PAGE_SIZE,
            writer=e['T_CRYPTO'],
            readers=[e['U_Linux_Public']]),
        Channel(
            name='Trusted Crypto <- Untrusted Linux Public',
            memory_size=6 * PAGE_SIZE,
            writer=e['U_Linux_Public'],
            readers=[e['T_CRYPTO']]),
        ##
        Channel(
            name='Untrusted Linux Public -> Untrusted App',
            memory_size=2 * PAGE_SIZE,
            writer=e['U_Linux_Public'],
            readers=[e['U_App']]),
        Channel(
            name='Untrusted Linux Public <- Untrusted App',
            memory_size=2 * PAGE_SIZE,
            writer=e['U_App'],
            readers=[e['U_Linux_Public']])
    ]

    executors_list = list(executors.values())

    #memory_regions = executors_list + channels
    memory_regions = executors_list + list(channels2.values())
    c = channels2

    # Specification of distinct cache isolation domains.
    cache_isolation_domains = [
        {e['Kernel']},  # Cache isolation domain 1: Kernel only
        # Cache isolation domain 2: Trusted subjects only
        {e['T_CRYPTO'], e['T_APP'], c['TC_2_TA'], c['TA_2_TC']},
        {e['U_Linux_VS_V']},  # Cache isolation domain 3: VS-Vertr
        {e['U_Linux_VS_NfD_1']},  # Cache isolation domain 4: NfD-1
        {e['U_Linux_VS_NfD_2']},  # Cache isolation domain 5: NfD-2
        {e['U_Linux_Public'],  # Cache isolation domain 6: Public and Untrusted App
         e['U_App'], c['UPUB_2_UA'], c['UA_2_UPUB']},
        {c['TC_2_UVertr'], c['UVertr_2_TC']},      # Cache isolation domains
        {c['TC_2_UNFD1'], c['UNFD1_2_TC']},  # to prevent mutual interference
        {c['TC_2_UNFD2'], c['UNFD2_2_TC']},  # from executors of
        {c['TC_2_UPUB'], c['UPUB_2_TC']},    # different cache isolation domains
    ]

    # Specify which CPU must be used by executor.
    executor_cpu_constraints = {
        e['Kernel']:            {cpu_cores[0]},    # Kernel must only use CPU core 0
        e['T_CRYPTO']:          {cpu_cores[1]},    # Trusted subjects must only
        e['T_APP']:             {cpu_cores[1]},    # use CPU core 1
        e['U_Linux_VS_V']:      {cpu_cores[2], cpu_cores[3]},  # Rest of the system use CPU core 2 and 3
        e['U_Linux_VS_NfD_1']:  {cpu_cores[2], cpu_cores[3]},
        e['U_Linux_VS_NfD_2']:  {cpu_cores[2], cpu_cores[3]},
        e['U_Linux_Public']:    {cpu_cores[2], cpu_cores[3]},
        e['U_App']:             {cpu_cores[2], cpu_cores[3]}
    }

    system = System(
        hardware=hardware,
        memory_regions=memory_regions,
        page_color_to_page_address_mapping_dump_file="data/page_color_to_page_address_mapping_dump.pkl")

    logging.info("Cache colors (Cache color = lists of affected sets by one memory page regarding one level of cache):")
    PageColoringModelPrettyPrinter.print_cache_colors(system)

    logging.info("Page colors (Page color = lists of affected sets by one memory page regarding all levels of caches):")
    PageColoringModelPrettyPrinter.print_page_colors(system)

    logging.info("System page colors (System page color: CPU + Page color):")
    PageColoringModelPrettyPrinter.print_system_page_colors(system)

    logging.info("Memory regions:")
    PageColoringModelPrettyPrinter.print_memory_regions(system)

    logging.info("Cache isolation domains:")
    PageColoringModelPrettyPrinter.print_cache_isolation_domains(cache_isolation_domains)

    logging.info("Executor-CPU constraints:")
    PageColoringModelPrettyPrinter.print_executor_cpu_constraints(executor_cpu_constraints)

    logging.info("Color assignment (with cache isolation domains method):")
    PageColoringModelPrettyPrinter.print_bar()

    assignment = ASPColorAssigner.get_assignment(system, cache_isolation_domains, executor_cpu_constraints)
    ASPColorAssigner.apply_assignment(assignment)

    PageColoringModelPrettyPrinter.print_color_assignment(system)

    # TODO: Number of unassigned page colors.

    logging.info("Unassigned system page colors:")
    PageColoringModelPrettyPrinter.print_unassigned_system_page_colors(system, assignment)

    logging.info("Assigning pages.")
    PageAssigner.assign_pages_simple(system)
    logging.info("Assigning pages. Finished.")
    # TODO: Print MemoryRegion to address space mapping
    PageColoringModelPrettyPrinter.print_page_assignment(system)

    # logging.info("Clingo output:")
    # ClingoPrinter.print_executors(executors)
    # ClingoPrinter.print_channels(channels)
    # ClingoPrinter.print_cpus(cpu_cores)
    # ClingoPrinter.print_executor_cpu_constraints(executor_cpu_constraints)
    # ClingoPrinter.print_cache_colors(system)
    # ClingoPrinter.print_page_colors(system)
    # ClingoPrinter.print_cache_isolation_domains(cache_isolation_domains)


if __name__ == "__main__":
    main()
