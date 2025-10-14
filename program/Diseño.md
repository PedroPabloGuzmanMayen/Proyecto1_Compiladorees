# Diseño del código intermedio

Para la generación de código intermedio, se usará la siguiente sintaxis: 


## Reglas generales del TAC

1. **Forma básica:** `t = a op b`
2. **Operaciones soportadas:** `+, -, *, /, >, <, >=, <=, ==, !=, &&, ||`
3. **Temporales:** `t1, t2, t3, …` se generan y reciclan automáticamente.
4. **Etiquetas:** `L1, L2, L3, …` marcan puntos de salto (`goto`).
5. **Parámetros:** se pasan explícitamente con la palabra clave `param`.
6. **Funciones y clases:** se delimitan con `func … endfunc` y `class … endclass`.

---

## Declaraciones y asignaciones

Estas no cambiaran mucho con respecto al lenguaje original, simplemente se quitará el tipo de dato pues luego del análisis semántico se asume que ya se verificó que todas las operaciones y asignaciones son válidas. Si la expresión lo requiere, se hará uso de temporales. 

### Ejemplo

Código fuente:
```compiscript
x: int = 1 + 2;
```

TAC:
```compiscript
x = 1 + 2
```



