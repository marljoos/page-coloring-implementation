# TODOs
* Take care of "set dueling"
* Testing / Unit tests
* Add shared/private attribute to Caches
* Move Color stuff from Hardware to System, Colors are more related to the System than to the Hardware

# Postponed TODOs
* Split L1 instruction cache & L1 data cache
* Take care of reserved memory.
* Specification of bootstrap processor in Hardware class needed?

# DONE
* must somehow model shared memory (channels)
* assign_memory_consumer_colors is too naive, list of interference domains don't have to be disjoint.
* Take care of CPUs.
* Take care of several level of caches (L2, L1).
* Implement cache isolation domains method
* Add System class to simplify ColorAssignment method interfaces
    * Integrate print_memory_consumer method into this class
* Add name to subject/executors/memory consumers
* Noch einmal über interference domains nachdenken. Wenn sich Subjekt 1 und Subjekt 2 gegenseitig stören 
  dürfen, dann gilt das implizit auch für ihre Channels untereinander.
  Ggf. einfach eine Warning ausgeben, dass Farben gespart werden könnten, statt implizit die Channels in
  die gleiche interference domain zuzuordnen.
* Cache isolation domains method
    * Implement CPU isolation domains
    * Implement Subject->CPU constraints for color assignment
* Take care of complex indexing in L3 cache. / Indexing function
* Rename MemoryRegion to MemoryRegion
* Add address space assignment method. / Concrete assignment of pages (MemoryAllocator)
