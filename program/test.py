from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic_analizer import semantic_analyzer

OUTPUT_FILE = "resultado_pruebas.txt"

def run_semantic_analysis(code_snippet: str):
    input_stream = InputStream(code_snippet)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    tree = parser.program()
    analyzer = semantic_analyzer()
    analyzer.visit(tree)
    return analyzer

def test_case(name: str, code: str, expect_ok: bool, f):
    f.write("\n" + "="*70 + "\n")
    f.write(f"PRUEBA: {name}\n")
    f.write("="*70 + "\n")
    f.write("Código:\n" + code + "\n\n")

    try:
        analyzer = run_semantic_analysis(code)
        ok = (len(analyzer.errors) == 0)
        if ok:
            f.write("✅ Análisis semántico exitoso (sin errores)\n")
        else:
            f.write("⚠️  Análisis completado con errores:\n")
            for i, err in enumerate(analyzer.errors, 1):
                f.write(f"  {i}. {err}\n")

        f.write("\n" + "-"*40 + "\n")
        f.write("TABLA DE SÍMBOLOS\n")
        f.write("-"*40 + "\n")
        analyzer.global_table.print_table(output=f)  # <-- ajustar para escribir al archivo

        # Veredicto contra expectativa
        passed = (ok == expect_ok)
        outcome = "PASÓ" if passed else "FALLÓ"
        exp_str = "OK" if expect_ok else "ERROR"
        f.write(f"\nResultado de la prueba: {outcome} (se esperaba {exp_str})\n")
        return passed

    except Exception as e:
        f.write(f"❌ Error fatal al ejecutar la prueba: {e}\n")
        import traceback
        f.write(traceback.format_exc() + "\n")
        return False


def main():
    tests = [
        ("Variable simple", "let x: integer = 5;", True),
        ("Variable sin tipo explícito (debe fallar)", "var y = 3;", False),
        ("Constante con tipo e init", "const PI: integer = 314;", True),
        ("Constante sin inicializador (debe fallar)", "const C: integer;", False),

        # Arrays
        ("Array 1D correcto", "let a: integer[] = [1,2,3];", True),
        ("Array 2D rectangular", "let m: integer[][] = [[1,2],[3,4]];", True),
        ("Array no rectangular (debe fallar)", "let j: integer[][] = [[1,2],[3]];", False),
        ("Array heterogéneo (debe fallar)", "let h: integer[] = [1, \"x\"];", False),
        ("Array vacío con tipo anotado", "let s: string[] = [];", True),

        # Funciones y return
        ("Función con retorno int correcto",
         """function add(a: integer, b: integer): integer {
                let r: integer = a + b;
                return r;
            }""", True),

        ("Función retorno tipo incorrecto (debe fallar)",
         """function bad(a: integer): integer {
                return "x";
            }""", False),

        ("Función retorna array 1D correcto",
         """function f(): integer[] {
                return [1,2,3];
            }""", True),

        ("Función retorna array con dimensión incorrecta (debe fallar)",
         """function g(): integer[] {
                return [[1]];
            }""", False),

        ("Función void con return (debe fallar)",
         """function h() {
                return 5;
            }""", False),

        # Control de flujo
        ("If con condición booleana", "let p: integer = 1; if (true) { let x: integer = 1; } else { let y: integer = 5; } let a: integer = 4;", True),
        ("If con condición no booleana (debe fallar)", "if (1) { let x: integer = 1; }", False),
        ("While con condición booleana", "while (true) { let a: integer = 1; }", True),
        ("While con condición no booleana (debe fallar)", "while (1) { let a: integer = 1; }", False),
        ("For con condición booleana",
         """for (let i: integer = 0; true; i = i + 1) { let k: integer = 1; }""", True),
        ("For con condición no booleana (debe fallar)",
         """for (let i: integer = 0; 1; i = i + 1) { let k: integer = 1; }""", False),

        # Try/Catch
        ("Try/Catch válido",
         """try { let a: integer = 1; } catch (e) { let msg: string = "err"; }""", True),
        ("Catch con id duplicado (debe fallar)",
         """try { let a: integer = 0; } catch (e) { let e: integer = 1; }""", False),

        # Switch
        ("Switch válido",
         """let x: integer = 2;
            switch (x) {
                case 1: { let a: integer = 10; }
                case 2: { let b: integer = 20; }
                default: { let c: integer = 0; }
            }""", True),
        ("Switch con case duplicado (debe fallar)",
         """let x: integer = 2;
            switch (x) {
                case 1: { let a: integer = 10; }
                case 1: { let b: integer = 20; }
            }""", False),

        # ======== NUEVAS: ARITMÉTICAS ========
        ("Arit: suma de enteros", "let a: integer = 1 + 2;", True),
        ("Arit: precedencia * sobre +", "let a: integer = 1 + 2 * 3;", True),
        ("Arit: modulo válido", "let a: integer = 7 % 3;", True),
        ("Arit: resta inválida con string (debe fallar)", "let a: integer = 1 - \"x\";", False),
        ("Arit: suma inválida boolean+int (debe fallar)", "let a: integer = true + 1;", False),

        # ======== NUEVAS: RELACIONALES ========
        ("Rel: menor que válido", "let b: boolean = 1 < 2;", True),
        ("Rel: <= válido", "let b: boolean = 2 <= 2;", True),
        ("Rel: > con string (debe fallar)", "let b: boolean = \"a\" > \"b\";", False),

        # ======== NUEVAS: IGUALDAD ========
        ("Eq: ints iguales", "let b: boolean = 3 == 3;", True),
        ("Eq: tipos distintos (debe fallar)", "let b: boolean = 1 == true;", False),

        # ======== NUEVAS: LÓGICAS ========
        ("Log: AND válido", "let b: boolean = true && false;", True),
        ("Log: OR válido", "let b: boolean = true || false;", True),
        ("Log: mezcla inválida (debe fallar)", "let b: boolean = 1 && true;", False),

        # ======== NUEVAS: UNARIOS ========
        ("Un: negación booleana", "let b: boolean = !false;", True),
        ("Un: menos unario válido", "let x: integer = -5;", True),
        ("Un: menos unario inválido (debe fallar)", "let x: integer = -\"a\";", False),
        ("Un: negación inválida (debe fallar)", "let b: boolean = !1;", False),

        # ======== NUEVAS: EXP COMPLEJA ========
        ("Mixta: !(1<2 && 3<4) || false", "let b: boolean = !(1 < 2 && 3 < 4) || false;", True),


        # ======= CONTINUE INVÁLIDO =====
        ("Continue inválido",
         """let x: integer = 2;
            continue;
            break;""", False),

        # === LLAMADA A FUNCION ====

        ("LLamada a función",
         """function add(a: integer, b: integer): integer {
                let r: integer = a + b;
                return r;
            }

            let c: integer = add(1,2);
            """, True),

        ("Foreach válido en array 1D",
         """let arr: integer[] = [1,2,3];
        foreach (x in arr) {
        let y: integer = x + 1;
        }""", True),

        ("Foreach válido en array 2D",
         """let mat: integer[][] = [[1,2],[3,4]];
        foreach (row in mat) {
            foreach (val in row) {
                let z: integer = val;
            }
        }""", True),

        ("Foreach sobre no-array (debe fallar)",
        """let a: integer = 5;
            foreach (x in a) {
                let y: integer = x;
            }""", False),

        ("No debe fallar", 
         """

function crearContador(): integer {
  function siguiente(): integer {
    return 1;
  }
  return siguiente();
}
     
        """, True),
        ("No sér", 
         """
const hola: Integer = 1*4+3

         """, True)

        

    ]

    passed = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for name, code, expect_ok in tests:
            if test_case(name, code, expect_ok, f):
                passed += 1

        total = len(tests)
        f.write("\n" + "="*70 + "\n")
        f.write("RESUMEN\n")
        f.write("="*70 + "\n")
        f.write(f"Pruebas pasadas: {passed}/{total} ({(passed/total)*100:.1f}%)\n")
        if passed == total:
            f.write("🎉 ¡Todas las pruebas pasaron conforme a lo esperado!\n")
        else:
            f.write("⚠️  Algunas pruebas no se comportaron como se esperaba. \n")

if __name__ == "__main__":
    main()
