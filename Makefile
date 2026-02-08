.PHONY: dev pre-commit lint complex unit infra-tests deploy compare-openapi coverage-tests e2e destroy

dev pre-commit lint complex unit infra-tests deploy compare-openapi coverage-tests e2e destroy:
	@$(MAKE) -C src/backend $@
