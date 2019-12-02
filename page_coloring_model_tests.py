import unittest
from itertools import cycle

from page_coloring_model import ColorAssigner, Hardware, Cache, Subject


class TestColorAssignment(unittest.TestCase):
    def setUp(self) -> None:
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
            [Cache(total_capacity=(32 * 1024), associativity=8, cacheline_capacity=64, flushed=True,
                   page_size=PAGE_SIZE)
             for _ in range(0, len(cpu_cores))]
        l2_caches = \
            [Cache(total_capacity=(256 * 1024), associativity=8, cacheline_capacity=64, page_size=PAGE_SIZE)
             for _ in range(0, len(cpu_cores) // 2)]
        l3_caches = [
            Cache(total_capacity=6 * (1024 ** 2), associativity=12, cacheline_capacity=64, page_size=PAGE_SIZE)]

        assert (len(l2_caches) == 2), "#ASSMS-CACHE-CONFIG-1"
        assert (len(l3_caches) == 1), "#ASSMS-CACHE-CONFIG-2"

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

        self.hardware = Hardware(cpu_cache_config=cpu_cache_config, page_size=PAGE_SIZE)

    def test_assign_by_naive(self):
        example_memory_consumers = {
            'Subj1': Subject(4096),
            'Subj2': Subject(4096),
            'Subj3': Subject(4096),
            'Subj4': Subject(4096)
        }
        assignment = ColorAssigner.get_assignment_by_naive(
            hardware=self.hardware, all_memory_consumers=example_memory_consumers
        )

        mc = example_memory_consumers

        expected_assignment = {
            mc['Subj1']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[0], 0),
            mc['Subj2']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[1], 0),
            mc['Subj3']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[2], 0),
            mc['Subj4']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[3], 0)
        }

        self.assertDictEqual(assignment, expected_assignment)

    #def test_assign_by_security_label(self):
    #    self.assertEqual(True, False)

    #def test_assign_by_interference_domains(self):
    #    self.assertEqual(True, False)

    def test_assign_by_cache_isolation_domains(self):
        example_memory_consumers = {
            'Subj1': Subject(4096),
            'Subj2': Subject(4096),
            'Subj3': Subject(4096),
            'Subj4': Subject(4096)
        }
        assignment = ColorAssigner.get_assignment_by_naive(
            hardware=self.hardware, all_memory_consumers=example_memory_consumers
        )

        mc = example_memory_consumers

        expected_assignment = {
            mc['Subj1']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[0], 0),
            mc['Subj2']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[1], 0),
            mc['Subj3']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[2], 0),
            mc['Subj4']: Hardware.SystemPageColor(self.hardware.get_cpu_cores()[3], 0)
        }

        self.assertDictEqual({}, expected_assignment)


if __name__ == '__main__':
    unittest.main()
