from register_allocator import RegisterAllocator

class MIPSGenerator:
    def __init__(self, quadruples, symbol_table, offsets=None):
        self.quads = quadruples
        self.sym = symbol_table
        self.offsets = offsets or {}
        self.regs = RegisterAllocator()
        self.lines = []
        self.pending_args = []
        self.current_function = None
        self.callers_waiting = []
        self.pending_funcion = []

    def _emit(self, txt):
        self.lines.append(txt)

    # =====================================================
    # FRAME SIZE
    # =====================================================
    def _frame_size(self, func_name):
        local_bytes = self.offsets.get(func_name, 0)
        reserved = 8  # RA + old FP
        total = local_bytes + reserved
        if total % 8 != 0:
            total += (8 - total % 8)
        return total

    # =====================================================
    # LOAD
    # =====================================================
    def _load(self, name):
        # --- constantes ---
        if isinstance(name, str) and (name.isdigit() or (name.startswith("-") and name[1:].isdigit())):
            reg = self.regs.get_reg_for("const_" + name)
            self._emit(f"li {reg}, {name}")
            return reg

        # --- temporales t1, t2, ... ---
        if isinstance(name, str) and name.startswith("t"):
            return self.regs.get_reg_for(name)

        # --- parámetros de la función actual ---
        func_sym = None
        if self.current_function:
            func_sym = self.sym.lookup_global(self.current_function)

        if func_sym and hasattr(func_sym, "params") and func_sym.params and name in func_sym.params:
            idx = func_sym.params.index(name)
            reg = self.regs.get_reg_for(name)

            # a0..a3
            if idx == 0:
                src = "$a0"
            elif idx == 1:
                src = "$a1"
            elif idx == 2:
                src = "$a2"
            elif idx == 3:
                src = "$a3"
            else:
                # parámetro 4+ (no deberías usarlos aún, pero por si acaso)
                off = 4 + 4 * (idx - 4)
                self._emit(f"lw {reg}, {off}($fp)")
                return reg

            self._emit(f"move {reg}, {src}")
            return reg

        # --- variable normal (global/local) ---
        sym = self.sym.lookup_global(name)
        if sym:
            reg = self.regs.get_reg_for(name)
            self._emit(f"lw {reg}, {sym.offset}($fp)")
            return reg

        # --- fallback: 0 ---
        reg = self.regs.get_reg_for(name)
        self._emit(f"li {reg}, 0")
        return reg

    # =====================================================
    # STORE
    # =====================================================
    def _store(self, name, reg):

        # temporal
        if isinstance(name, str) and name.startswith("t"):
            self.regs.bind(reg, name)
            return

        sym = self.sym.lookup_global(name)
        if sym:
            self._emit(f"sw {reg}, {sym.offset}($fp)")
            return

        self._emit(f"# ERROR: variable desconocida {name}")

    # =====================================================
    # FLUSH PARAMS (CALLER SIDE)
    # =====================================================
    def _flush_args(self):
        for i, reg in enumerate(self.pending_args):
            self._emit(f"move $a{i}, {reg}")
        self.pending_args = []


    # =====================================================
    # GENERATE
    # =====================================================
    def generate(self, out_filename="program.s"):

        # prólogo general del programa
        self._emit(".data")
        self._emit(".text")
        self._emit(".globl main")
        self._emit(".globl _start")
        self._emit("_start:")
        self._emit("jal main")
        self._emit("li $v0, 10")
        self._emit("syscall")

        for op, a1, a2, res in self.quads:

            # ------------------------------------------------
            # FUNC
            # ------------------------------------------------
            if op == "FUNC":
                self.current_function = a1
                frame = self._frame_size(a1)

                self._emit(f"{a1}:")
                self._emit(f"addi $sp, $sp, -{frame}")
                self._emit("sw $ra, 0($sp)")
                self._emit("sw $fp, 4($sp)")
                self._emit("addi $fp, $sp, 4")

                func_sym = self.sym.lookup_global(a1)
                if func_sym and hasattr(func_sym, "params") and func_sym.params:
                    for i, pname in enumerate(func_sym.params):
                        psym = self.sym.lookup_global(pname)
                        if not psym:
                            continue
                        if i < 4:
                            self._emit(f"sw $a{i}, {psym.offset}($fp)")
                        else:
                            off = 4 + 4 * (i - 4)
                            tmp = self.regs.get_reg_for(f"arg{i}")
                            self._emit(f"lw {tmp}, {off}($sp)")
                            self._emit(f"sw {tmp}, {psym.offset}($fp)")

            # ------------------------------------------------
            # ENDFUNC
            # ------------------------------------------------
            elif op == "endfunc":
                frame = self._frame_size(a1)
                frame = frame * -1
                self._emit("lw $ra, -4($fp)")
                self._emit("lw $fp, 0($fp)")
                self._emit(f"addi $sp, $fp, -4")
                self._emit("jr $ra")

            # ------------------------------------------------
            # ASSIGN (=)
            # ------------------------------------------------
            elif op == "=":
                r = self._load(a1)
                self._store(res, r)

            # ------------------------------------------------
            # ARITH
            # ------------------------------------------------
            elif op in ["+", "-", "*", "/"]:
                r1 = self._load(a1)
                r2 = self._load(a2)
                rd = self.regs.get_reg_for(res)

                if op == "+":
                    self._emit(f"add {rd}, {r1}, {r2}")
                elif op == "-":
                    self._emit(f"sub {rd}, {r1}, {r2}")
                elif op == "*":
                    self._emit(f"mul {rd}, {r1}, {r2}")
                elif op == "/":
                    self._emit(f"div {r1}, {r2}")
                    self._emit(f"mflo {rd}")

                self._store(res, rd)

            # ------------------------------------------------
            # RELATIONAL
            # ------------------------------------------------
            elif op in ["<", ">", "<=", ">=", "==", "!="]:
                r1 = self._load(a1)
                r2 = self._load(a2)
                rd = self.regs.get_reg_for(res)

                if op == "<":
                    self._emit(f"slt {rd}, {r1}, {r2}")
                elif op == ">":
                    self._emit(f"slt {rd}, {r2}, {r1}")
                elif op == "<=":
                    self._emit(f"slt {rd}, {r2}, {r1}")
                    self._emit(f"xori {rd}, {rd}, 1")
                elif op == ">=":
                    self._emit(f"slt {rd}, {r1}, {r2}")
                    self._emit(f"xori {rd}, {rd}, 1")
                elif op == "==":
                    self._emit(f"xor {rd}, {r1}, {r2}")
                    self._emit(f"sltiu {rd}, {rd}, 1")
                elif op == "!=":
                    self._emit(f"xor {rd}, {r1}, {r2}")
                    self._emit(f"sltu {rd}, $zero, {rd}")

                self._store(res, rd)

            # ------------------------------------------------
            # PRINT
            # ------------------------------------------------
            elif op == "PRINT":
                r = self._load(res)
                self._emit(f"move $a0, {r}")
                self._emit("li $v0, 1")
                self._emit("syscall")
                self._emit("li $v0, 11")
                self._emit("li $a0, 10")
                self._emit("syscall")

            # ------------------------------------------------
            # LABEL
            # ------------------------------------------------
            elif op == "label":
                self._emit(f"{res}:")

            # ------------------------------------------------
            # IF / GOTO
            # ------------------------------------------------
            elif op == "if":
                cond = self._load(a1)
                self._emit(f"bne {cond}, $zero, {res}")

            elif op == "goto":
                self._emit(f"j {a1}")

            # ------------------------------------------------
            # PARAM (CALLER)
            # ------------------------------------------------
            elif op == "param":
                r = self._load(a1)
                self.pending_args.append(r)

            # ------------------------------------------------
            # CALL_FUNC
            # ------------------------------------------------
            elif op == "CALL_FUNC":
                fname = a1
                self._emit(f"# CALL {fname}")

                # pasar argumentos a a0..a3
                self._flush_args()

                self._emit(f"jal {fname}")

                if res:
                    rd = self.regs.get_reg_for(res)
                    self._emit(f"move {rd}, $v0")
                    self._store(res, rd)
            # ------------------------------------------------
            # RETURN
            # ------------------------------------------------
            elif op == "RETURN":
                if a1:
                    r = self._load(a1)
                    self._emit(f"move $v0, {r}")

                self._emit("lw $ra, -4($fp)")
                self._emit("lw $fp, 0($fp)")
                self._emit("addi $sp, $fp, -4")
                self._emit("jr $ra")

        # =================================================
        # WRITE FILE
        # =================================================
        with open(out_filename, "w") as f:
            for line in self.lines:
                f.write(line + "\n")
