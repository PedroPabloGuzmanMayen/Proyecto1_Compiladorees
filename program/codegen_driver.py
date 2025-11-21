import sys
from antlr4 import FileStream, CommonTokenStream
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic_analizer import semantic_analyzer
from tac_generator import tac_generator
from mips_generator import MIPSGenerator

def main(argv):
    src = argv[1]
    input_stream = FileStream(src, encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    analyzer = semantic_analyzer()
    analyzer.visit(tree)

    if analyzer.errors:
        print("Se encontraron errores semánticos:")
        for err in analyzer.errors:
            print("  ", err)
        return

    print("Análisis semántico OK. Generando TAC...")
    tac_gen = tac_generator(analyzer.global_table)
    tac_gen.visit(tree)

    quads = tac_gen.quadruple_table
    analyzer.global_table.print_table()
    print("SCOPE MAP")
    print(analyzer.global_table.scope_map)

    offsets = tac_gen.offsets
    print(offsets)
    print("Antes de agrupar")
    
    for i, (op, arg1, arg2, res) in enumerate(quads.quadruples):
        print(op, arg1, arg2, res)
    
    print("Luego de agrupar")

    quads = quads.group_by_blocks()
    for i, (op, arg1, arg2, res) in enumerate(quads):
        print(op, arg1, arg2, res)
    


    mg = MIPSGenerator(quads, analyzer.global_table, offsets)
    mg.generate("program.s")
    print("Archivo program.s generado.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 codegen_driver.py <archivo_fuente.compiscript>")
        sys.exit(1)
    main(sys.argv)

