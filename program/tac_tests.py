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
    return analyzer, intermediate_code_generator

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

let arr: integer[] = [1, 2, 3];
let sum: integer = 0;
foreach (elem in arr) {
    sum = sum + elem;
}

let j: integer = 0;
do {
    j = j + 1;
} while (j < 2);
"""

analyzer, intermediate_code_generator = run_code_gen(code)

def byte_size(elem):
    t = getattr(elem, "type", "")
    t = t.lower() if isinstance(t, str) else ""
    if t in ("integer", "int"):
        base = 4
    elif t in ("float", "double"):
        base = 8
    elif t in ("boolean", "bool"):
        base = 1
    else:
        base = 8
    dim = getattr(elem, "dim", None)
    count = dim if isinstance(dim, int) and dim > 0 else 1
    return base * count

print("\n--- OFFSETS GLOBAL ---")
for name, elem in analyzer.global_table.elements.items():
    off = getattr(elem, "offset", None)
    print(f"{name:10s} type={getattr(elem,'type',None):8s} dim={getattr(elem,'dim',None)!s:4s} offset={off}")

print("\n--- OFFSETS POR SCOPE ---")
for scope_key, st in getattr(analyzer.global_table, "scope_map", {}).items():
    base = intermediate_code_generator.offsets.get(scope_key, 0)
    print(f"\nScope: {scope_key}  base_offset={base}")
    if hasattr(st, "elements"):
        for name, elem in st.elements.items():
            off = getattr(elem, "offset", None)
            print(f"  {name:10s} type={getattr(elem,'type',None):8s} dim={getattr(elem,'dim',None)!s:4s} offset={off}")

for scope_key, st in getattr(analyzer.global_table, "scope_map", {}).items():
    if not hasattr(st, "elements"):
        continue
    prev_end = 0
    for name, elem in st.elements.items():
        off = getattr(elem, "offset", None)
        assert off is not None and off >= 0, f"Sin offset o negativo para {name} en {scope_key}"
        size = byte_size(elem)
        if off < prev_end:
            print(f"WARNING: posible solapamiento en {name} en {scope_key} (offset {off} < prev_end {prev_end})")
        prev_end = max(prev_end, off + size)

print("\n[OK] Memory allocator: offsets impresos y comprobaciones básicas realizadas.")

