from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic_analizer import semantic_analyzer

def run_semantic_analysis(code_snippet: str):
    input_stream = InputStream(code_snippet)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    analyzer = semantic_analyzer()
    analyzer.visit(tree)
    return analyzer

def test_case(name: str, code: str, expect_ok: bool):
    print("\n" + "="*70)
    print(f"PRUEBA: {name}")
    print("="*70)
    print("Código:\n" + code + "\n")

    try:
        analyzer = run_semantic_analysis(code)
        ok = (len(analyzer.errors) == 0)
        if ok:
            print("✅ Análisis semántico exitoso (sin errores)")
        else:
            print("⚠️  Análisis completado con errores:")
            for i, err in enumerate(analyzer.errors, 1):
                print(f"  {i}. {err}")
        print("\n" + "-"*40)
        print("TABLA DE SÍMBOLOS")
        print("-"*40)
        analyzer.global_table.print_table()

        # Veredicto contra expectativa
        passed = (ok == expect_ok)
        outcome = "PASÓ" if passed else "FALLÓ"
        exp_str = "OK" if expect_ok else "ERROR"
        print(f"\nResultado de la prueba: {outcome} (se esperaba {exp_str})")
        return passed

    except Exception as e:
        print(f"❌ Error fatal al ejecutar la prueba: {e}")
        import traceback; traceback.print_exc()
        # Si esperábamos ERROR semántico, un error fatal no cuenta como correcto.
        return False

def main():


    tests = [
        # ----------------- Variables / Constantes -----------------
        ("Variable simple", "let x: integer = 5;", True),
        ("Variable sin tipo explícito (debe fallar)", "var y = 3;", False),
        ("Constante con tipo e init", "const PI: integer = 314;", True),
        ("Constante sin inicializador (debe fallar)", "const C: integer;", False),

        # ----------------- Arrays -----------------
        ("Array 1D correcto", "let a: integer[] = [1,2,3];", True),
        ("Array 2D rectangular", "let m: integer[][] = [[1,2],[3,4]];", True),
        ("Array no rectangular (debe fallar)", "let j: integer[][] = [[1,2],[3]];", False),
        ("Array heterogéneo (debe fallar)", "let h: integer[] = [1, \"x\"];", False),
        ("Array vacío con tipo anotado", "let s: string[] = [];", True),

        # ----------------- Funciones y return -----------------
        ("Función con retorno int correcto",
         """function add(a: integer, b: integer): integer {
                let r: integer = a + b;
                return r;
            }""",
         True),

        ("Función retorno tipo incorrecto (debe fallar)",
         """function bad(a: integer): integer {
                return "x";
            }""",
         False),

        ("Función retorna array 1D correcto",
         """function f(): integer[] {
                return [1,2,3];
            }""",
         True),

        ("Función retorna array con dimensión incorrecta (debe fallar)",
         """function g(): integer[] {
                return [[1]];
            }""",
         False),

        ("Función void con return (debe fallar)",
         """function h() {
                return 5;
            }""",
         False),

        # ----------------- If / While / For -----------------
        ("If con condición booleana", "let p: integer = 1; if (true) { let x: integer = 1; }", True),
        ("If con condición no booleana (debe fallar)", "if (1) { let x: integer = 1; }", False),
        ("While con condición booleana", "while (true) { let a: integer = 1; }", True),
        ("While con condición no booleana (debe fallar)", "while (1) { let a: integer = 1; }", False),

        # For según la implementación: init ; cond ; incr
        ("For con condición booleana",
         """for (let i: integer = 0; true; i = i + 1) {
                let k: integer = 1;
            }""",
         True),

        ("For con condición no booleana (debe fallar)",
         """for (let i: integer = 0; 1; i = i + 1) {
                let k: integer = 1;
            }""",
         False),

        # ----------------- Try/Catch -----------------
        ("Try/Catch válido",
         """try {
                let a: integer = 1;
            } catch (e) {
                let msg: string = "err";
            }""",
         True),

        ("Catch con id duplicado (debe fallar)",
         """try {
                let a: integer = 0;
            } catch (e) {
                let e: integer = 1; // duplicado
            }""",
         False),

        # ----------------- Switch -----------------
        ("Switch válido",
         """let x: integer = 2;
            switch (x) {
                case 1: { let a: integer = 10; }
                case 2: { let b: integer = 20; }
                default: { let c: integer = 0; }
            }""",
         True),

        ("Switch con case duplicado (debe fallar)",
         """let x: integer = 2;
            switch (x) {
                case 1: { let a: integer = 10; }
                case 1: { let b: integer = 20; } // duplicado
            }""",
         False),
    ]

    passed = 0
    for name, code, expect_ok in tests:
        if test_case(name, code, expect_ok):
            passed += 1

    total = len(tests)
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Pruebas pasadas: {passed}/{total} ({(passed/total)*100:.1f}%)")
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron conforme a lo esperado!")
    else:
        print("⚠️  Algunas pruebas no se comportaron como se esperaba. Revisa los casos reportados arriba.")

if __name__ == "__main__":
    main()
