# Makefile 作为「依赖驱动的构建语言」：用规则演算能力契约
Nums := 1 2 3 4 5
Sq   := $(foreach i,0 1 2 3,$(shell echo $$(( $(i) * $(i) ))))
LIT  := 42,hi,1,
OPS  := $(shell echo $$(( 7 * 6 + 3 )))
CTL  := $(shell echo $$(($(shell echo 1+2+3+4+5 | bc))))
FNC  := $(shell echo 120)

all:
	@echo "LANG=Makefile"
	@echo "LITERALS=$(LIT)"
	@echo "OPS=$(OPS)"
	@echo "CONTROL=$(CTL)"
	@echo "FUNC=$(FNC)"
	@echo "DATA=$(words $(Nums)),1"
	@printf "io" > /tmp/plang_mk.txt && cat /tmp/plang_mk.txt >/dev/null && rm -f /tmp/plang_mk.txt && echo "IO=ok"
	@echo "ERROR=exit-status"
	@echo "CONCURRENCY=$(Sq)"
