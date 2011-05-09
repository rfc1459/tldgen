all: tld_test

.PHONY: clean

clean:
	@echo "  [CLEAN] tld_test tld_tab.h tld_stats.txt"
	@rm -f tld_test tld_tab.h tld_stats.txt

tld_test: tld_tab.h tld_test.c
	@echo "  [CC] tld_test"
	@gcc -O2 -o $@ tld_test.c

tld_tab.h: tldgen fsm.py tlds-alpha-by-domain.txt
	@echo "  [GEN] tld_tab.h"
	@./tldgen
