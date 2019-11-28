# TODOs
* Split L1 instruction cache & L1 data cache
* Take care of complex indexing in L3 cache.
* Take care of reserved memory.
* Noch einmal über interference domains nachdenken. Wenn sich Subjekt 1 und Subjekt 2 gegenseitig stören 
  dürfen, dann gilt das implizit auch für ihre Channels untereinander.
  Ggf. einfach eine Warning ausgeben, dass Farben gespart werden könnten, statt implizit die Channels in
  die gleiche interference domain zuzuordnen.
* Implement CPU isolation domains
* Implement Subject->CPU constraints for color assignment

## DONE
* must somehow model shared memory (channels)
* assign_memory_consumer_colors is too naive, list of interference domains don't have to be disjoint.
* Take care of CPUs.
* Take care of several level of caches (L2, L1).