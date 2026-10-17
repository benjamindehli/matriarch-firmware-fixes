#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
# Dump a disassembly listing from the Ghidra project in work/ghidra.
# Usage: tools/listing.sh <outfile> <start> <end> [<start> <end> ...]   (C28x word addresses)
# Env: GHIDRA_INSTALL_DIR (Ghidra 12.1.x with the TMS320C28x module), JAVA_HOME,
#      PROGRAM (program name in the project, default matriarch_v1.3.0_0x88000.bin)
R=$(cd "$(dirname "$0")/.." && pwd)
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR to your Ghidra install}"
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$R/work/ghidra" matriarch \
  -process "${PROGRAM:-matriarch_v1.3.0_0x88000.bin}" -noanalysis -readOnly \
  -scriptPath "$R/tools/ghidra_scripts" -postScript DumpListing.java "$@" > /dev/null 2>&1
cat "$1"
