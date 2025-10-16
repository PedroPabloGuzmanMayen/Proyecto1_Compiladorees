class Quadruple():
    def __init__(self):
        self.quadruples = []


    def insert_into_table(self, operator, arg1, arg2, temp):
        self.quadruples.append((operator, arg1, arg2, temp))

    def write_to_console(self, filename="intermediate_code.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== CÓDIGO INTERMEDIO (TAC / Cuádruplos) ===\n\n")
            for i, (op, arg1, arg2, res) in enumerate(self.quadruples):
                f.write(f"{i:03d}: ({op}, {arg1}, {arg2}, {res})\n")
        print(f"[✅] Código intermedio guardado en '{filename}'")

