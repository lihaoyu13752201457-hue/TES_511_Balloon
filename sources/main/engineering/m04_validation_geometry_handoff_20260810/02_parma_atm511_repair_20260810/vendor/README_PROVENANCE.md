# Official PARMA source snapshot provenance

- Download URL: `https://phits.jaea.go.jp/expacs/data/parma_cpp.zip`
- Downloaded: 2026-08-10 20:59:11 +08:00
- Archived file: `parma_cpp_official_20260810.zip`
- Size: 1,427,174 bytes
- SHA-256: `dc9c1ed3e1dfb04c7e1ca3ab0967d18b538535cc0c0dcb9055c6c256993bca33`
- Extracted, unmodified snapshot: `parma_cpp_official_20260810/`

The download is current as of the stated date, but the bundled `Readme.txt`
still identifies the C++ program as `PARMA Version 4.10 (2021/03/21)`.  The
archive itself contains newer data: for example, `input/FFPtable.day` has an
archive timestamp of 2026-03-27 and extends through 2026.  The public EXPACS
release number and this retained C++ source banner therefore must not be
silently treated as the same version identifier.

The line calculation in this work package is bound to the archived files and
their hashes, not to a version number inferred from the website.  The wrapper
under `../code/` calls the archived routines without editing them.  It does not
use `/tmp` or the separate external mirror as production authority.

Key hashes:

| File | SHA-256 |
| --- | --- |
| `subroutines.cpp` | `620cab2b58bac6bf996dcc0ad9a33b7bc113a4d768eb2f17b97788a500010c1b` |
| `main.cpp` | `ac7da5a9d7b1b0a0951e277bd0246dcd95d995a247d761642e7f6e0b032c665b` |
| `main-generator.cpp` | `5e0f127880b048e4a5dcb204757004aea96d9982417ac7bb7baed378e3896fdb` |
| `input/elemag/flux511keV.inp` | `30b57b1aba9d62c956ed323ec49f8d7d36a8d1ae9fa7eb149708f9c412fc59c0` |
| `input/FFPtable.day` | `a3886c29d475fd5d84f145ee645d66b7e9bc9807cbeeec1c295ba38381052043` |
