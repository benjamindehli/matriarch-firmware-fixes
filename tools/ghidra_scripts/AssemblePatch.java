// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
//
// Assemble C28x instructions with the processor module's SLEIGH assembler and print the encoded words.
// Args: <outfile> then groups of "@<wordaddr>" followed by instruction lines, e.g.
//   out.txt @0xa2000 "CMPB AH,#0x0" "LB 0x8c56b" @0x8c5bd "LCR 0xa2000"
// Run against a program opened read-only: the patched bytes are disassembled and printed, never saved.
import ghidra.app.plugin.assembler.Assembler;
import ghidra.app.plugin.assembler.Assemblers;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.listing.Instruction;
import java.io.FileWriter;
import java.io.PrintWriter;

public class AssemblePatch extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        AddressSpace sp = currentProgram.getAddressFactory().getDefaultAddressSpace();
        Assembler asm = Assemblers.getAssembler(currentProgram);
        Address at = null;
        for (int k = 1; k < a.length; k++) {
            if (a[k].startsWith("@")) {
                at = sp.getTruncatedAddress(Long.decode(a[k].substring(1)), true);
                continue;
            }
            clearListing(at, at.add(7));
            Instruction in = asm.assemble(at, a[k]).next();
            byte[] b = in.getBytes();
            StringBuilder w = new StringBuilder();
            for (int i = 0; i + 1 < b.length; i += 2) w.append(String.format("%04x ", ((b[i + 1] & 0xff) << 8) | (b[i] & 0xff)));
            out.println(String.format("%s %-12s %-28s <- %s", in.getAddress(), w.toString().trim(), in, a[k]));
            at = in.getAddress().add(b.length);
        }
        out.close();
    }
}
