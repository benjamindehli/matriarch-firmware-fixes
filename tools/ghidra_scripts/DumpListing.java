// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
// Dump disassembly with raw words. Args: <outfile> <startWordAddr> <endWordAddr> [...more pairs]
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;

public class DumpListing extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        AddressSpace sp = currentProgram.getAddressFactory().getDefaultAddressSpace();
        for (int k = 1; k + 1 < a.length; k += 2) {
            Address s = sp.getTruncatedAddress(Long.decode(a[k]), true);
            Address e = sp.getTruncatedAddress(Long.decode(a[k + 1]), true);
            out.println("; ---- " + a[k] + " .. " + a[k + 1]);
            InstructionIterator it = currentProgram.getListing().getInstructions(new AddressSet(s, e), true);
            while (it.hasNext()) {
                Instruction in = it.next();
                StringBuilder w = new StringBuilder();
                byte[] b = in.getBytes();
                for (int i = 0; i + 1 < b.length; i += 2) w.append(String.format("%04x ", ((b[i + 1] & 0xff) << 8) | (b[i] & 0xff)));
                Function f = getFunctionContaining(in.getAddress());
                String lbl = getSymbolAt(in.getAddress()) != null ? getSymbolAt(in.getAddress()).getName() + ":" : "";
                out.println(String.format("%s %-20s %-12s %s", in.getAddress(), w.toString().trim(), lbl, in));
            }
        }
        out.close();
    }
}
