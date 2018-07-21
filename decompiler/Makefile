MAKEFILE := $(lastword $(MAKEFILE_LIST))
BASE_DIR := $(realpath $(dir $(MAKEFILE)))
ILSPY_DIR := $(BASE_DIR)/ILSpy
BUILD_DIR := $(BASE_DIR)/build
GIT_BIN := git
MSBUILD_BIN := msbuild
LIBS := Mono.Cecil.dll ICSharpCode.Decompiler.dll ICSharpCode.NRefactory.dll ICSharpCode.NRefactory.CSharp.dll

SOURCES := decompile.cs

.SUFFIXES: .cs .exe
.PHONY: all clean depends


all: decompile.exe


depends:
	$(GIT_BIN) -C $(BASE_DIR) submodule init
	$(GIT_BIN) -C $(BASE_DIR) submodule update
	$(GIT_BIN) -C $(ILSPY_DIR) submodule init
	$(GIT_BIN) -C $(ILSPY_DIR) submodule update
	$(GIT_BIN) -C $(ILSPY_DIR) reset --hard
	$(GIT_BIN) -C $(ILSPY_DIR) apply $(BASE_DIR)/short-circuit.patch
	$(eval csproj := ILSpy/ICSharpCode.Decompiler/ICSharpCode.Decompiler.csproj)
	$(MSBUILD_BIN) $(csproj)
	$(MSBUILD_BIN) /property:OutputPath=$(BUILD_DIR) $(csproj)

decompile.exe: depends
	$(eval flags := $(foreach lib,$(LIBS),-r:$(BUILD_DIR)/$(lib)))
	mcs -debug -out:$(BUILD_DIR)/$(patsubst %.cs,%.exe,$@) $(flags) $(SOURCES)

clean:
	test -d $(BUILD_DIR) && rm -rf $(BUILD_DIR)
