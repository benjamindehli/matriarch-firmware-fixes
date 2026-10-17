// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
// Export decompiled C for every function, plus a per-function list of the
// MMIO/RAM addresses it references. Output dir: script arg 0.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import java.io.*;
import java.util.*;

public class ExportDecomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        File dir = new File(getScriptArgs()[0]);
        dir.mkdirs();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        PrintWriter c = new PrintWriter(new FileWriter(new File(dir, "decomp.c")));
        PrintWriter refs = new PrintWriter(new FileWriter(new File(dir, "refs.tsv")));
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int n = 0;
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f = it.next();
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            c.println("// ===== " + f.getName() + " @ " + f.getEntryPoint());
            if (r != null && r.decompileCompleted()) c.println(r.getDecompiledFunction().getC());
            else c.println("// decompile failed: " + (r == null ? "null" : r.getErrorMessage()));
            for (Address a : f.getBody().getAddresses(true)) {
                for (Reference ref : getReferencesFrom(a)) {
                    if (ref.getReferenceType().isData())
                        refs.println(f.getName() + "\t" + a + "\t" + ref.getToAddress() + "\t" + ref.getReferenceType());
                }
            }
            n++;
        }
        c.close(); refs.close();
        println("exported " + n + " functions");
    }
}
