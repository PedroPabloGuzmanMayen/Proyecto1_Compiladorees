from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic_analizer import semantic_analyzer
from tac_generator import tac_generator


def run_code_gen(code_snippet: str):
    input_stream = InputStream(code_snippet)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    analyzer = semantic_analyzer()
    analyzer.visit(tree)
    intermediate_code_generator = tac_generator(analyzer.global_table)
    intermediate_code_generator.visit(tree)
    intermediate_code_generator.quadruple_table.write_to_console()


code = """ let hola:integer = (1+3)-(4*(5/2))
let adios:integer = (1+2)
"""

run_code_gen(code)