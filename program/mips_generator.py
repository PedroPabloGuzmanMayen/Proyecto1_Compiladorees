from register_allocator import RegisterAllocator

class MIPSGenerator:
    def __init__(self, quadruples, symbol_table, offsets=None):
        self.quads = quadruples
        self.sym = symbol_table
        self.offsets = offsets or {}
        self.regs = RegisterAllocator()
        self.lines = []

    def _emit(self, txt):
        self.lines.append(txt)

    def _compute_stack_needed(self):
        # tomamos el máximo offset de los scopes 
        max_off = 0
        try:
            for v in (self.offsets.values() if isinstance(self.offsets, dict) else []):
                if isinstance(v, int) and v > max_off:
                    max_off = v
        except Exception:
            max_off = 0
        # añadir espacio para spills y margen
        spill_estimate = (len(self.regs.pool) + 8) * 4
        total = max_off + spill_estimate + 64
        # alinear a 16
        if total % 16 != 0:
            total += 16 - (total % 16)
        return total

    def _lookup_symbol(self, name):
        if not name:
            return None
        try:
            return self.sym.lookup_global(name)
        except Exception:
            return None

    def _load_operand(self, operand):
        if operand is None:
            return None
        # constante numérica 
        try:
            if isinstance(operand, str) and (operand.isdigit() or (operand.startswith("-") and operand[1:].isdigit())):
                reg = self.regs.get_reg_for(f"const_{operand}")
                self._emit(f"li {reg}, {operand}")
                return reg
        except Exception:
            pass
        # temporal 
        if isinstance(operand, str) and operand.startswith("t"):
            # si ya tiene registro, devuélvelo
            rinfo = self.regs.find_by_content(operand)
            if rinfo:
                return rinfo.name
            # si fue spill, cargar desde stack
            if self.regs.has_spill(operand):
                reg = self.regs.get_reg_for(operand)
                off = self.regs.get_spill_offset(operand)
                # offset en bytes desde base de spills; base será añadido al $sp reservado
                self._emit(f"lw {reg}, {off}($sp)")
                return reg
            # si no hay info, simplemente reservar registro y asumir que el valor será producido por operación
            reg = self.regs.get_reg_for(operand)
            return reg
        # variable identificador (buscar en symbol table)
        sym = self._lookup_symbol(operand)
        if sym:
            reg = self.regs.get_reg_for(operand)
            addr = getattr(sym, "address", None)
            if addr is None:
                addr = getattr(sym, "offset", 0)
            self._emit(f"lw {reg}, {addr}($sp)")
            return reg
        # fallback: reservar registro e intentar cargar 0
        reg = self.regs.get_reg_for(operand)
        self._emit(f"li {reg}, 0")
        return reg

    def _store_result(self, dest, reg):
        if dest is None:
            return
        # si destino es temporal, se deja en registro 
        if isinstance(dest, str) and dest.startswith("t"):
            self.regs.mark_dirty(reg)
            # el contenido ya se asoció con el temporal por get_reg_for
            return
        # si destino es variable, buscamos su offset en symbol table
        sym = self._lookup_symbol(dest)
        if sym:
            addr = getattr(sym, "address", None)
            if addr is None:
                addr = getattr(sym, "offset", 0)
            self._emit(f"sw {reg}, {addr}($sp)")
            return
        # fallback: no sabemos dónde guardarlo
        self._emit(f"# store: no se conoce cómo guardar {dest}")

    def generate(self, out_filename="program.s"):
        stack_size = self._compute_stack_needed()
        # indicar al allocator la base de spills 
        self.regs.set_spill_base(stack_size)

        # prologue
        self._emit(f"addi $sp, $sp, -{stack_size}")
        self._emit(f"# reserva {stack_size} bytes para variables y spills")

        # traducir cuadruplos
        for op, a1, a2, res in self.quads:
            if op == "=":
                src_reg = self._load_operand(a1)
                if src_reg:
                    # si el resultado es una variable o temporal
                    dest = res
                    self._store_result(dest, src_reg)

            elif op in ["+", "-", "*", "/"]:
                r1 = self._load_operand(a1)
                r2 = self._load_operand(a2)
                rd = self.regs.get_reg_for(res)
                if op == "+":
                    self._emit(f"add {rd}, {r1}, {r2}")
                elif op == "-":
                    self._emit(f"sub {rd}, {r1}, {r2}")
                elif op == "*":
                    # usar mul o mult/mflo
                    self._emit(f"mul {rd}, {r1}, {r2}")
                elif op == "/":
                    self._emit(f"div {r1}, {r2}")
                    self._emit(f"mflo {rd}")
                self._store_result(res, rd)

            elif op in [">", "<", ">=", "<=", "==", "!="]:
                r1 = self._load_operand(a1)
                r2 = self._load_operand(a2)
                rd = self.regs.get_reg_for(res)
                if op == "==":
                    self._emit(f"xor {rd}, {r1}, {r2}")
                    # resultado 0 -> iguales; queremos 1 si iguales:
                    self._emit(f"sltiu {rd}, {rd}, 1")
                elif op == "!=":
                    self._emit(f"xor {rd}, {r1}, {r2}")
                    self._emit(f"sltu {rd}, $zero, {rd}")
                elif op == "<":
                    self._emit(f"slt {rd}, {r1}, {r2}")
                elif op == ">":
                    self._emit(f"slt {rd}, {r2}, {r1}")
                elif op == "<=":
                    self._emit(f"slt {rd}, {r2}, {r1}")
                    self._emit(f"xori {rd}, {rd}, 1")
                elif op == ">=":
                    self._emit(f"slt {rd}, {r1}, {r2}")
                    self._emit(f"xori {rd}, {rd}, 1")
                self._store_result(res, rd)

            elif op == "PRINT":
                r = self._load_operand(res)
                if r:
                    self._emit(f"move $a0, {r}")
                    self._emit("li $v0, 1")
                    self._emit("syscall")

            elif op == "label":
                lbl = res.rstrip(":") if isinstance(res, str) else res
                self._emit(f"{lbl}:")
            elif op == "if":
                # forma: (if, cond, 'goto', Ltrue)
                cond_reg = self._load_operand(a1)
                if cond_reg:
                    # si cond != 0 -> branch a label
                    lbl = res
                    self._emit(f"bne {cond_reg}, $zero, {lbl}")
            elif op == "goto":
                label = a1 or res
                self._emit(f"j {label}")
            else:
                self._emit(f"# op no manejada: {op} {a1} {a2} {res}")

        self._emit(f"addi $sp, $sp, {stack_size}")

        with open(out_filename, "w", encoding="utf-8") as f:
            for line in self.lines:
                f.write(line + "\n")
