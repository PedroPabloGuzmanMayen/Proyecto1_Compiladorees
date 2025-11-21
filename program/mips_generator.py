from register_allocator import RegisterAllocator
from symbolTable import Symbol_table


class MIPSGenerator:
    def __init__(self, quadruples, symbol_table, offsets=None):
        self.quads = quadruples
        self.sym: Symbol_table = symbol_table
        self.offsets = offsets or {}          # ya no lo usamos mucho, pero no estorba
        self.regs = RegisterAllocator()

        self.data_section = []
        self.text_section = []

        self.current_function = None
        self.current_symtable: Symbol_table = symbol_table
        self.pending_args = []

        self.string_counter = 0
        self.in_func_header = False      # para ignorar param en definición
        self.func_param_regs = {}        # nombre -> $a0, $a1, etc.


    def _emit_text(self, txt):
        self.text_section.append(txt)

    def _emit_data(self, txt):
        self.data_section.append(txt)


    def _frame_size(self, func_name: str) -> int:
        return 8


    def _load(self, name):
  
        if isinstance(name, str) and (
            name.isdigit() or (name.startswith("-") and name[1:].isdigit())
        ):
            reg = self.regs.get_reg_for(f"const_{name}")
            self._emit_text(f"li {reg}, {name}")
            return reg


        if isinstance(name, str) and name.startswith("t"):
            return self.regs.get_reg_for(name)


        if (
            self.current_function is not None
            and name in self.func_param_regs
        ):
            return self.func_param_regs[name]


        if isinstance(name, str) and name.startswith("\"") and name.endswith("\""):
            label = f"str_{self.string_counter}"
            self.string_counter += 1
            text_clean = name[1:-1]
            self._emit_data(f'{label}: .asciiz "{text_clean}"')
            return label

        psym = getattr(self.current_symtable, "elements", {}).get(name, None)
        gsym = getattr(self.sym, "elements", {}).get(name, None)

        reg = self.regs.get_reg_for(name)

        if gsym is not None and (self.current_function is None or self.current_symtable.scope == "Global"):
            self._emit_text(f"lw {reg}, {name}")
            return reg

        self._emit_text(f"# WARN: variable {name} usada sólo en registro {reg}")
        return reg


    def _store(self, name, reg):
        # temporales t1, t2, ...
        if isinstance(name, str) and name.startswith("t"):
            self.regs.bind(reg, name)
            return

        psym = getattr(self.current_symtable, "elements", {}).get(name, None)
        gsym = getattr(self.sym, "elements", {}).get(name, None)

  
        if gsym is not None and (self.current_function is None or self.current_symtable.scope == "Global"):
            self._emit_text(f"sw {reg}, {name}")
            return

        fixed = self.regs.get_reg_for(name)   
        if fixed != reg:
            self._emit_text(f"move {fixed}, {reg}")
        self._emit_text(f"# WARN: variable {name} sólo en registro {fixed} (no se guarda en memoria)")


    def _flush_args(self):
        for i, r in enumerate(self.pending_args):
            self._emit_text(f"move $a{i}, {r}")
        self.pending_args = []


    def group_by_blocks(self):
        scopes = {"main": [self.quads[0]]}
        current = ["main"]

        for op, a1, a2, res in self.quads[1:]:
            if op == "FUNC":
                current.append(a1)
                scopes[a1] = [(op, a1, a2, res)]
                continue
            if op == "endfunc":
                scopes[a1].append((op, a1, a2, res))
                current.pop()
                continue

            scopes[current[-1]].append((op, a1, a2, res))

        general = []
        if "main" in scopes:
            general += scopes["main"]
        for k in scopes:
            if k != "main":
                general += scopes[k]
        return general

 
    def generate(self, out_filename="program.s"):
        quads = self.group_by_blocks()


        # .data: variables globales
        for name, entry in self.sym.elements.items():
            if getattr(entry, "kind", None) == "variable":
                self._emit_data(f"{name}: .word 0")

        # .text: _start
        has_main = any(op == "FUNC" and a1 == "main" for op, a1, _, _ in quads)
        exit_emitted = False

        self._emit_text(".globl _start")
        self._emit_text("_start:")

        if has_main:
            
            self._emit_text("jal main")
            self._emit_text("li $v0, 10")
            self._emit_text("syscall")
        else:
            # Programa sin main: ejecutamos código global
            self._emit_text("# No main()")

        # Recorrer cuádruplos

        for op, a1, a2, res in quads:

          
            if op == "FUNC" and not has_main and not exit_emitted:
                self._emit_text("li $v0, 10")
                self._emit_text("syscall")
                exit_emitted = True
             

            if op == "FUNC":
                self.current_function = a1
                self.in_func_header = True
                self.func_param_regs = {}

                func_key = f"function_{a1}"
                func_tab = getattr(self.sym, "scope_map", {}).get(func_key, None)

                if isinstance(func_tab, Symbol_table):
                    self.current_symtable = func_tab
                else:
                    self.current_symtable = self.sym

                frame = self._frame_size(a1)

                self._emit_text(f"{a1}:")
                # Prologue simple: FP y RA en stack
                self._emit_text(f"addi $sp, $sp, -{frame}")
                self._emit_text("sw $fp, 0($sp)")
                self._emit_text("sw $ra, 4($sp)")
                self._emit_text("move $fp, $sp")

                # Mapear parámetros a registros
                func_sym = self.sym.elements.get(a1)
                if func_sym and getattr(func_sym, "params", None):
                    for i, pinfo in enumerate(func_sym.params):
                        pname = pinfo["name"]
                        if i < 4:
                            self.func_param_regs[pname] = f"$a{i}"
    

                continue
            # FIN DE FUNCIÓN
            if op == "endfunc":
                self._emit_text(f"# endfunc {a1}")
                self._emit_text("lw $fp, 0($sp)")
                self._emit_text("lw $ra, 4($sp)")
                self._emit_text("addi $sp, $sp, 8")
                self._emit_text("jr $ra")

                self.current_function = None
                self.current_symtable = self.sym
                self.in_func_header = False
                self.func_param_regs = {}
                continue

            if op != "param":
                self.in_func_header = False


            if op == "=":
                r = self._load(a1)
                self._store(res, r)
                continue

    
            if op in ["+", "-", "*", "/"]:
                r1 = self._load(a1)
                r2 = self._load(a2)
                rd = self.regs.get_reg_for(res)

                if op == "+":
                    self._emit_text(f"add {rd}, {r1}, {r2}")
                elif op == "-":
                    self._emit_text(f"sub {rd}, {r1}, {r2}")
                elif op == "*":
                    self._emit_text(f"mul {rd}, {r1}, {r2}")
                elif op == "/":
                    self._emit_text(f"div {r1}, {r2}")
                    self._emit_text(f"mflo {rd}")

                self._store(res, rd)
                continue


            # RELACIONALES
            if op in ["<", "<=", ">", ">=", "==", "!="]:
                r1 = self._load(a1)
                r2 = self._load(a2)
                rd = self.regs.get_reg_for(res)

                if op == "<":
                    self._emit_text(f"slt {rd}, {r1}, {r2}")
                elif op == ">":
                    self._emit_text(f"slt {rd}, {r2}, {r1}")
                elif op == "<=":
                    self._emit_text(f"slt {rd}, {r2}, {r1}")
                    self._emit_text(f"xori {rd}, {rd}, 1")
                elif op == ">=":
                    self._emit_text(f"slt {rd}, {r1}, {r2}")
                    self._emit_text(f"xori {rd}, {rd}, 1")
                elif op == "==":
                    self._emit_text(f"xor {rd}, {r1}, {r2}")
                    self._emit_text(f"sltiu {rd}, {rd}, 1")
                elif op == "!=":
                    self._emit_text(f"xor {rd}, {r1}, {r2}")
                    self._emit_text(f"sltu {rd}, $zero, {rd}")

                self._store(res, rd)
                continue


            if op == "PRINT":
                if isinstance(res, str) and res.startswith("\""):
                    label = self._load(res)
                    self._emit_text(f"la $a0, {label}")
                    self._emit_text("li $v0, 4")
                    self._emit_text("syscall")
                else:
                    r = self._load(res)
                    self._emit_text(f"move $a0, {r}")
                    self._emit_text("li $v0, 1")
                    self._emit_text("syscall")

                self._emit_text("li $v0, 11")
                self._emit_text("li $a0, 10")
                self._emit_text("syscall")
                continue

  
            if op == "label":
                lbl = (res or "").rstrip(":")
                self._emit_text(f"{lbl}:")
                continue

            if op == "if":
                cond = self._load(a1)
                self._emit_text(f"bne {cond}, $zero, {res}")
                continue

            if op == "goto":
                self._emit_text(f"j {a1}")
                continue

            if op == "param":
                if self.current_function is not None and self.in_func_header:
         
                    continue
                r = self._load(a1)
                self.pending_args.append(r)
                continue

            if op == "CALL_FUNC":
                fname = a1
                self._flush_args()
                self._emit_text(f"jal {fname}")
                if res:
                    rd = self.regs.get_reg_for(res)
                    self._emit_text(f"move {rd}, $v0")
                    self._store(res, rd)
                continue

       
            if op == "RETURN":
                if a1 is not None:
                    r = self._load(a1)
                    self._emit_text(f"move $v0, {r}")
                # epílogo de retorno
                self._emit_text("# return epilogue")
                self._emit_text("lw $fp, 0($sp)")
                self._emit_text("lw $ra, 4($sp)")
                self._emit_text("addi $sp, $sp, 8")
                self._emit_text("jr $ra")
                continue

    
        if not has_main and not exit_emitted:
            self._emit_text("li $v0, 10")
            self._emit_text("syscall")

        with open(out_filename, "w") as f:
            f.write(".data\n")
            for d in self.data_section:
                f.write(d + "\n")

            f.write(".text\n")
            for t in self.text_section:
                f.write(t + "\n")
