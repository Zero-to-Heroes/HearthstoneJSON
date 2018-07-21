MAKEFILE := $(lastword $(MAKEFILE_LIST))
BASE_DIR := $(realpath $(dir $(MAKEFILE)))
BUILD_DIR := $(BASE_DIR)/build
PROJ_DIR := $(BASE_DIR)/proto-extractor/mono-extractor
CSPROJ := $(PROJ_DIR)/mono-extractor.csproj
MSBUILD_BIN := msbuild
PKG_FILE := $(BASE_DIR)/proto-extractor/hsproto-packaging.ini

.SUFFIXES: .cs .exe
.PHONY: all clean depends

all: mono-extractor.exe

depends:
	test -d $(BUILD_DIR) || mkdir -p $(BUILD_DIR)
	cp $(PKG_FILE) $(BUILD_DIR)/packaging.ini

mono-extractor.exe: depends
	$(MSBUILD_BIN) /property:OutputPath=$(BUILD_DIR) /property:Configuration=Release $(CSPROJ)

clean:
	$(MSBUILD_BIN) /t:Clean $(CSPROJ)
	test -d $(BUILD_DIR) && rm -rf $(BUILD_DIR)
