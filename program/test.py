#!/usr/bin/env python3

from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic_analizer import semantic_analyzer

def test_case(code_snippet, test_name):
    """Prueba un caso y muestra resultados detallados"""
    print(f"\n{'='*60}")
    print(f"PRUEBA: {test_name}")
    print(f"{'='*60}")
    print(f"Código:\n{code_snippet}\n")
    
    try:
        # Crear el análisis
        input_stream = InputStream(code_snippet)
        lexer = CompiscriptLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = CompiscriptParser(stream)
        
        # Parsear el programa
        tree = parser.program()
        print("✅ Parsing exitoso")
        
        # Análisis semántico
        analyzer = semantic_analyzer()
        analyzer.visit(tree)
        
        if not analyzer.errors:
            print("✅ Análisis semántico exitoso")
        else:
            print("⚠️  Análisis completado con errores")
        
        # Mostrar tabla de símbolos
        print(f"\n{'-'*40}")
        print("TABLA DE SÍMBOLOS")
        print(f"{'-'*40}")
        analyzer.global_table.print_table()
        
        # Mostrar errores si los hay
        if analyzer.errors:
            print(f"\n{'-'*40}")
            print("ERRORES ENCONTRADOS")
            print(f"{'-'*40}")
            for i, error in enumerate(analyzer.errors, 1):
                print(f"{i}. {error}")
        
        return len(analyzer.errors) == 0
        
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 PRUEBAS FINALES DEL ANALIZADOR SEMÁNTICO")
    
    tests_passed = 0
    total_tests = 0
    
    # Prueba 1: Variable simple
    total_tests += 1
    if test_case("let x: integer = 5;", "Variable simple"):
        tests_passed += 1
    
    # Prueba 2: Constante
    total_tests += 1
    if test_case("const PI: integer = 314;", "Constante con tipo"):
        tests_passed += 1
    
    # Prueba 3: Constante sin tipo (inferencia)
    total_tests += 1
    if test_case("const GREETING = \"Hola\";", "Constante sin tipo (inferencia)"):
        tests_passed += 1
    
    # Prueba 4: Variable sin inicializador
    total_tests += 1
    if test_case("let flag: boolean;", "Variable sin inicializador"):
        tests_passed += 1
    
    # Prueba 5: Array simple
    total_tests += 1
    if test_case("let numbers: integer[] = [1, 2, 3];", "Array simple"):
        tests_passed += 1
    
    # Prueba 6: Función simple
    total_tests += 1
    if test_case("""function add(a: integer, b: integer): integer {
    let result: integer = a + b;
    return result;
}""", "Función con parámetros y tipo de retorno"):
        tests_passed += 1
    
    # Prueba 7: Función sin tipo de retorno
    total_tests += 1
    if test_case("""function greet(name: string) {
    print("Hola " + name);
}""", "Función sin tipo de retorno"):
        tests_passed += 1
    
    # Prueba 8: Múltiples declaraciones
    total_tests += 1
    if test_case("""const MAX: integer = 100;
let count: integer = 0;
let name: string = "test";
let items: string[];""", "Múltiples declaraciones mixtas"):
        tests_passed += 1
    
    # Prueba 9: Error esperado - variable duplicada
    total_tests += 1
    print(f"\n{'='*60}")
    print("PRUEBA: Error esperado - variable duplicada")
    print(f"{'='*60}")
    result = test_case("""let x: integer = 5;
let x: string = "duplicado";""", "Variable duplicada (debe fallar)")
    if not result:  # Esperamos que falle
        tests_passed += 1
        print("✅ Error detectado correctamente")
    else:
        print("❌ Error no detectado")
    
    # Prueba 10: Error esperado - constante sin inicializador
    total_tests += 1
    print(f"\n{'='*60}")
    print("PRUEBA: Error esperado - constante sin valor")
    print(f"{'='*60}")
    result = test_case("const PI: integer;", "Constante sin inicializador (debe fallar)")
    if not result:  # Esperamos que falle
        tests_passed += 1
        print("✅ Error detectado correctamente")
    else:
        print("❌ Error no detectado")
    
    # Resumen
    print(f"\n{'='*60}")
    print(f"RESUMEN DE PRUEBAS")
    print(f"{'='*60}")
    print(f"Pruebas pasadas: {tests_passed}/{total_tests}")
    print(f"Porcentaje de éxito: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 ¡Todas las pruebas pasaron!")
    else:
        print("⚠️  Algunas pruebas fallaron")

if __name__ == "__main__":
    main()