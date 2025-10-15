# Diseño del código intermedio

Para la generación de código intermedio, se usará la siguiente sintaxis: 

---

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
--- 

## Expresiones aritméticas

Estas harán uso de temporales si son muy complejas. 

### Ejemplo

Código fuente:
```compiscript
x: int = 1 * (3 + 1) / 4;
```
TAC:
```compiscript
t1 = 3 + 1
t2 = 1 * t1
t3 = t2 / 4
x = t3
```
---

## Expresiones booleanas

Hará uso de el número de línea de código para determinar donde debe dar el salto. 

### Ejemplo

Código fuente:
```compiscript
if (a > b && c == d) {
  print("ok");
}
```

TAC
```compiscript
t1 = a > b
t2 = c == d
t3 = t1 && t2
if t3 goto L1
goto L2
L1:
print("ok")
L2:
```

---

## Ciclos While

### Ejemplo

Código fuente: 
```compiscript
while (x < 10) {
  x = x + 1;
}
```

TAC:
```compiscript
L1:
t1 = x < 10
if t1 goto L2
goto L3
L2:
t2 = x + 1
x = t2
goto L1
L3:
```

---

## Ciclos for

### Ejemplo

Código fuente:
```compiscript
for (i = 0; i < 5; i = i + 1) {
  print(i);
}
```

TAC:
```compiscript
i = 0
L1:
t1 = i < 5
if t1 goto L2
goto L3
L2:
print(i)
t2 = i + 1
i = t2
goto L1
L3:
```

---

## Switch statements

### Ejemplo

Código fuente:
```compiscript
switch (x) {
  case 1:
    print("uno");
  case 2:
    print("dos");
  default:
    print("otro");
}
```

TAC:
```compiscript
t1 = x
if t1 == 1 goto L1
if t1 == 2 goto L2
goto L3

L1:
print("uno")
goto L4

L2:
print("dos")
goto L4

L3:
print("otro")

L4:
```

---

## Declaración de funciones

### Ejemplo

Código fuente
```compiscript
function add(a: integer, b: integer): integer {
  return a + b;
}
```

TAC:
```compiscript
func add, n_params=2, ret_type=integer
param a
param b
t1 = a + b
return t1
endfunc
```

---

## Llamada a funciones

Código fuente
```compiscript
add(1, 2);
```

TAC:
```compiscript
param 1
param 2
call add, 2
```

---

## Asignación del valor de retorno de una función

### Ejemplo

Código fuente
```compiscript
y = add(1, 2);
```

TAC:
```compiscript
param 1
param 2
call add, 2, tRet
y = tRet
```

---

## Delcaración de clases

### Ejemplo

Código fuente
```compiscript
y = add(1, 2);
```

TAC:
```compiscript
class Animal
field nombre

func constructor, n_params=1
param this
param nombre
this.nombre = nombre
return
endfunc

func hablar, n_params=1, ret_type=string
param this
t1 = this.nombre
t2 = t1 + " hace ruido."
return t2
endfunc
endclass
```

---

## Instanciación

### Ejemplo

Código fuente
```compiscript
a = new Animal("Perro");
a.hablar();
```

TAC:
```compiscript
param "Perro"
call Animal.constructor, 1, t1
a = t1
param a
call Animal.hablar, 1, t2
```

---








