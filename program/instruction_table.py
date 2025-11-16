class Quadruple():
    def __init__(self):
        self.quadruples = []
        self._temp_counter = 0

    def insert_into_table(self, operator, arg1, arg2, temp):
        self.quadruples.append((operator, arg1, arg2, temp))

    def add(self, operator, arg1, arg2, temp):
        self.insert_into_table(operator, arg1, arg2, temp)

    def new_temp(self):
        self._temp_counter += 1
        return f"t{self._temp_counter}"

    def write_to_console(self, filename="intermediate_code.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== CÓDIGO INTERMEDIO (TAC / Cuádruplos) ===\n\n")
            for i, (op, arg1, arg2, res) in enumerate(self.quadruples):
                f.write(f"{i:03d}: ({op}, {arg1}, {arg2}, {res})\n")
        print(f"Código intermedio guardado en '{filename}'")

    def write_tac(self, filename="intermediate_code.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== CÓDIGO INTERMEDIO (TAC / Cuádruplos) ===\n\n")
            for i, (op, arg1, arg2, res) in enumerate(self.quadruples):
                line = ""
                if op == "label":
                    line = f"{res}"
                elif op == "=":
                    if arg2 is None:
                        line = f"{res} = {arg1}"
                    else:
                        line = f"{res} = {arg1} {op} {arg2}"
                elif op in ["+", "-", "*", "/", ">", "<", ">=", "<=", "==", "!=", "&&", "||"]:
                    line = f"{res} = {arg1} {op} {arg2}"
                elif op == "[]":
                    line = f"{res} = {arg1}[{arg2}]"
                elif op == "[]=":
                    line = f"{res}[{arg2}] = {arg1}"
                elif op == "if":
                    line = f"if {arg1} goto {res}"
                elif op == "goto":
                    if arg1:
                        line = f"goto {arg1}"
                    elif res:
                        line = f"goto {res}"
                    else:
                        line = "goto"
                elif op == "FUNC":
                    line = f"func {arg1}, n_params={arg2}, ret_type={res}"
                elif op == "PRINT":
                    line = f"print {res}"
                elif op == "RETURN":
                    line = f"return {arg1 if arg1 else ''}"
                elif op == "endfunc":
                    line = "endfunc"
                elif op == "param":
                    line = f"param {arg1}"
                elif op == "call":
                    if res:
                        line = f"{res} = call {arg1}, {arg2}"
                    else:
                        line = f"call {arg1}, {arg2}"
                elif op == "length":
                    line = f"{res} = length {arg1}"
                elif op == "class":
                    line = f"class {arg1}"
                elif op == "endclass":
                    line = "endclass"
                elif op == "field":
                    line = f"field {arg1}"
                else:
                    line = f"# {op} {arg1 or ''} {arg2 or ''} {res or ''}".strip()
                f.write(f"{line}\n")
        print(f"TAC legible guardado en '{filename}'")
