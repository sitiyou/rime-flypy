ifeq ($(PREFIX),)
	PREFIX := /usr
endif

ifeq ($(RIME_DATA_DIR),)
	RIME_DATA_DIR := $(PREFIX)/share/rime-data
endif

dict:
	rime_deployer --compile flypyok.schema.yaml
	rime_deployer --compile flypydz.schema.yaml
	rime_deployer --compile flypy.schema.yaml

install-lua:
	install -vDm644 lua/*.lua lua/LICENSE.openfly -t $(DESTDIR)$(RIME_DATA_DIR)/lua


install: install-lua
# Build dict from source and install
	rm -rf build/*.txt > /dev/null 2>&1 || true
	install -vDm644 flypy*.yaml -t $(DESTDIR)$(RIME_DATA_DIR)
	install -vDm644 flypy/flypy*.yaml -t $(DESTDIR)$(RIME_DATA_DIR)/flypy
	install -vDm644 build/flypy* -t $(DESTDIR)$(RIME_DATA_DIR)/build

dist:
	tar -czvf rime-flypy.tar.gz flypy*.yaml flypy/*.yaml lua/*.lua lua/LICENSE.openfly

clean:
	rm -rf build/ > /dev/null 2>&1 || true

.PHONY: dict install dist clean

# Generate the fcitx5-rime user profile from this checkout.
.DEFAULT_GOAL := generate
PROFILE_DIR ?= $(or $(XDG_CONFIG_HOME),$(HOME)/.config)/rime-flypy
USER_RIME_DIR ?= $(or $(XDG_DATA_HOME),$(HOME)/.local/share)/fcitx5/rime
SHARED_RIME_DIR ?= /usr/share/rime-data
profile_cmd = python3 scripts/profile.py --personal "$(PROFILE_DIR)" --shared "$(SHARED_RIME_DIR)"

generate:
	$(profile_cmd) generate

verify:
	@set -eu; out=$$(mktemp -d); trap 'rm -rf "$$out"' EXIT; \
	version=$$(python3 -c 'import yaml; print(yaml.safe_load(open("flypy.dict.yaml"))["version"])'); \
	scripts/rime-flypy-dict --assets assets --output "$$out" --version "$$version"; \
	cmp flypy/flypy.primary.dict.yaml "$$out/flypy/flypy.primary.dict.yaml"
	$(profile_cmd) verify

install-user:
	$(profile_cmd) install --target "$(USER_RIME_DIR)"

.PHONY: generate verify install-user

# Independently reproduce the checked-in dictionaries from the matching official package.
verify-official:
	@test -n "$(SOURCE_DIR)" || { echo 'Set SOURCE_DIR to the official macOS package rime directory'; exit 2; }
	@set -eu; out=$$(mktemp -d); trap 'rm -rf "$$out"' EXIT; \
	version=$$(python3 -c 'import yaml; print(yaml.safe_load(open("flypy.dict.yaml"))["version"])'); \
	scripts/rime-flypy-dict --assets "$(SOURCE_DIR)/build" --output "$$out" --version "$$version"; \
	scripts/flypy-txt2yaml --source-dir "$(SOURCE_DIR)" --output-dir "$$out" --version "$$version"; \
	diff -r --exclude='flypy.user*.dict.yaml' flypy "$$out/flypy"; \
	cmp flypydz.dict.yaml "$$out/flypydz.dict.yaml"; cmp flypyok.dict.yaml "$$out/flypyok.dict.yaml"

.PHONY: verify-official

deploy: install-user
	busctl --user call org.fcitx.Fcitx5 /controller org.fcitx.Fcitx.Controller1 ReloadAddonConfig s rime

.PHONY: deploy

FCITX5_CONFIG_DIR ?= $(or $(XDG_CONFIG_HOME),$(HOME)/.config)/fcitx5
install-frontend:
	install -Dm644 profile/fcitx5-rime.conf "$(FCITX5_CONFIG_DIR)/conf/rime.conf"

deploy: install-frontend
.PHONY: install-frontend
