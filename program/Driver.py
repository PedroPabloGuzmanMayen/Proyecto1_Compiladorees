import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic_analizer import semantic_analyzer 

def main(argv):
    input_stream = FileStream(argv[1])
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program() 
    analyzer = semantic_analyzer()
    analyzer.visit(tree)

    # Mostrar errores o tabla de símbolos
    if analyzer.errors:
        print("Se encontraron errores semánticos:")
        for err in analyzer.errors:
            print("  ", err)
    else:
        print(" Análisis semántico completado sin errores.")

    print("\n--- TABLA DE SÍMBOLOS ---")
    analyzer.global_table.print_table()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 main.py <archivo_fuente.compiscript>")
        sys.exit(1)
    main(sys.argv)
