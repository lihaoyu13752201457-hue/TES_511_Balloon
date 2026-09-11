MEGALIB := /home/ubuntu/MEGAlib_Install/megalib-main
ROOT_CONFIG := $(MEGALIB)/external/root_v6.36.6/bin/root-config
G4_CONFIG := $(MEGALIB)/external/geant4_v10.02.p03/bin/geant4-config
CXX := g++
OPT := -O3 -mtune=native -fno-strict-aliasing -DNDEBUG
ROOT_CFLAGS := $(shell $(ROOT_CONFIG) --cflags)
ROOT_LIBS := $(shell $(ROOT_CONFIG) --glibs --libs)
G4_CFLAGS := $(filter-out -Wshadow -Woverloaded-virtual,$(shell $(G4_CONFIG) --cflags)) -DG4VIS_USE -Wno-deprecated-copy -Wno-overloaded-virtual
G4_LIBS := $(shell $(G4_CONFIG) --libs)
CXXFLAGS := $(OPT) -std=c++14 -Wall -Wno-deprecated -fPIC -D_REENTRANT -D___LINUX___ -D___CLING___ -Iinc -I$(MEGALIB)/include -I$(MEGALIB)/config $(ROOT_CFLAGS) $(G4_CFLAGS)
# Use legacy DT_RPATH deliberately: Geant4 10.2.3's libG4expat is an
# indirect dependency, and DT_RUNPATH is not searched transitively by glibc.
LDFLAGS := $(OPT) -L$(MEGALIB)/lib -Wl,--disable-new-dtags -Wl,-rpath,$(MEGALIB)/lib -Wl,-rpath,$(shell $(ROOT_CONFIG) --libdir) -Wl,-rpath,$(shell $(G4_CONFIG) --prefix)/lib
MEGA_LIBS := -lSivan -lGeomega -lCommonMisc -lCommonGui
CPP_FILES := $(filter-out src/MCCosima.cc src/M05Cosima.cc,$(wildcard src/*.cc))
OBJ_FILES := $(patsubst src/%.cc,build/%.o,$(CPP_FILES))
TARGET := bin/m05cosima

.PHONY: all clean
all: $(TARGET)

$(TARGET): $(OBJ_FILES) src/M05Cosima.cc
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) src/M05Cosima.cc $(OBJ_FILES) $(LDFLAGS) $(MEGA_LIBS) $(ROOT_LIBS) $(G4_LIBS) -lcrypto -lpthread -lThread -lMinuit -lMinuit2 -lGeom -lSpectrum -lTMVA -o $@

build/%.o: src/%.cc
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	@find build -maxdepth 1 -type f -name '*.o' -delete 2>/dev/null || true
	@find bin -maxdepth 1 -type f -name 'm05cosima' -delete 2>/dev/null || true
