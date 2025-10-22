ifeq ($(CONTAINER),container)
$(info Makefile enabled, proceeding ...)
else
$(error Error: Makefile disabled, exiting ...)
endif

ROOT_MAKEFILE:=$(abspath $(patsubst %/, %, $(dir $(abspath $(lastword $(MAKEFILE_LIST))))))

include $(ROOT_MAKEFILE)/.env

export
export PATH := $(PATH):$(shell pwd)/$(UV_INSTALL_DIR)
OLLAMA_MODEL?=gpt-oss:20b

$(eval UVEL := $(shell which uv && echo "true" || echo ""))
UVE = $(if ${UVEL},'uv',$(UV_INSTALL_DIR)/uv)

dev: setup
	$(UVE) sync --frozen --all-groups
	$(UVE) run lefthook uninstall 2>&1 || echo "not installed"
	$(UVE) run lefthook install

tests: setup
	$(UVE) sync --frozen --group test

build: setup
	$(UVE) sync --frozen

docs: setup
	$(UVE) sync --frozen --group docs

setup:
	which uv || [ -d "${UV_INSTALL_DIR}" ] || (curl -LsSf https://astral.sh/uv/install.sh | sh -s - --quiet)
	$(UVE) python install $(PYV)
	rm -rf .venv
	$(UVE) venv --python=$(PYV) --relocatable --link-mode=copy --seed
	$(UVE) pip install --upgrade pip
	$(UVE) run playwright install chromium || echo "failed to install playwright"


RAN := $(shell awk 'BEGIN{srand();printf("%d", 65536*rand())}')

runAct:
	echo "source .venv/bin/activate; rm /tmp/$(RAN)" > /tmp/$(RAN)
	bash --init-file /tmp/$(RAN)

runChecks:
	$(UVE) run lefthook run pre-commit --all-files -f

runDocs:
	$(UVE) run mkdocs build -f configs/dev/mkdocs.yml -d ../../public

serveDocs:
	$(UVE) run mkdocs serve -f configs/dev/mkdocs.yml

runTests:
	$(UVE) run tox

runBuild:
	$(UVE) build

runBump:
	$(UVE) run cz bump --files-only --yes --changelog
	git add .
	$(UVE) run cz version --project | xargs -i git commit -am "bump: release {}"

runUV:
	$(UVE) run $(CMD)

runLock runUpdate: %: export_%
# add all packages rquired to be build
	$(UVE) export --frozen --format requirements.txt > requirements.txt
	$(UVE) export --frozen --only-group dev --format requirements.txt > configs/dev/requirements.dev.txt
	$(UVE) export --frozen --only-group test --format requirements.txt > configs/dev/requirements.test.txt
	$(UVE) export --frozen --only-group docs --format requirements.txt > configs/dev/requirements.docs.txt

export_runLock:
	$(UVE) lock

export_runUpdate:
	$(UVE) lock -U

com commit:
	echo "" > .commit_msg
	@if curl -sf http://ollama:11434; then \
		$(MAKE) message; \
	else \
		$(UVE) run cz commit; \
	fi
	echo "" > .commit_msg

recom recommit:
	@if curl -sf http://ollama:11434; then \
		[ ! -s .commit_msg ] || (echo "Missing commit message!" && exit 1); \
		git commit -F .commit_msg; \
	else \
		$(UVE) run cz commit; \
	fi
	echo "" > .commit_msg

PROMPT=Generate a commit message in the Conventional Commits 1.0.0 format based on the following git diff. The commit message must: \n\
- Follow this structure: \n\
1. Commit type (e.g., feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert) \n\
2. Optional scope in parentheses (e.g., feat(auth):) \n\
3. A brief, lowercase description in present tense on the first line \n\
4. Optional body with detailed explanation (can use uppercase) \n\
5. Optional footer(s) with breaking changes, issue references (e.g., Closes \#123), or co-authors (e.g., Co-authored-by: Name) \n\
- Formatting rules: \n\
1. The first line must be entirely lowercase \n\
2. Body and footer may use uppercase letters \n\
3. Follow Conventional Commits 1.0.0 strictly \n\
4. Return only the commit message as plain text (no extra formatting, no markdown) \n\
5. Do NOT mention - no breaking changes \n\
6. Body lines must not be longer than 100 characters \n\
- Example: \n\
feat(auth): add user login API\n\
\n\
Added support for user login via OAuth2. This allows users to authenticate\n\
using their Google account.\n\
\n\
Closes \#42\n\


message:
	git diff --staged -- . ':(exclude)*requirements*.txt' | \
		jq -Rs --arg prompt "$(PROMPT)" '{"stream": false, "model": "$(OLLAMA_MODEL)", "prompt": (" <GIT_DIFF> " + . + " </GIT_DIFF> " + $$prompt)}' | \
		curl -s -X POST http://ollama:11434/api/generate \
			-H "Content-Type: application/json" \
			-d @- | \
		jq -r 'select(.done == true) | .response' > .commit_msg
	vim .commit_msg
	@if ! $(UVE) run cz check --commit-msg-file .commit_msg; then \
		echo "Commit message failed cz check. Aborting."; \
		echo "" > .commit_msg; \
		exit 1; \
	fi
	git commit -F .commit_msg
