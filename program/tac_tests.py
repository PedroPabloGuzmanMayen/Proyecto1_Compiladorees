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
    intermediate_code_generator.quadruple_table.write_tac("code.txt")

code = """ let hola:integer = (1+3)-(4*(5/2));

let adios: boolean = 1 < 2;
let hello: boolean = 1 == 2 || 2==1 || 1<3;

if (1<2){
    let hoo: integer = 1;
}
else {
    let mario: integer = 2;
}

let hi: integer = 1;
adios = true;

let x: integer = 2;
switch (x) {
    case 1: { let a: integer = 10; }
    case 2: { let b: integer = 20; }
    default: { let c: integer = 30; }
}

let i: integer = 0;
for (i = 0; i < 3; i = i + 1) {
    let x: integer = i;
}

let arr: integer[] = [1, 2, 3];
let v: integer = arr[1];
arr[0] = 10;

let sum: integer = 0;
foreach (elem in arr) {
    sum = sum + elem;
}

let j: integer = 0;
do {
    j = j + 1;
} while (j < 2);
"""

run_code_gen(code)

