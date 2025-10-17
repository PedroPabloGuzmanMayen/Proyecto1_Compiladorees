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

Estas harán uso de temporales si son muy complejas. El resultado final se asigna a la variable que tiene el valor de la operación. 

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

Hará uso de el número de línea de código para determinar donde debe dar el salto.  Si son muy compeljas va guardando los resultados intermedios en temporales 

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

Se crean 32 etiquetas: una de inicio y ahí se guarda el resultado de la condición que va a evaluar el ciclo; una de cuerpo que indica que se debe hacer si se cumple la condición, luego hacemos un salto de línea a la condición inicial para evaluar si debemos volver a repetir el procedimiento; finalmente se añade una etiqueta final que indica que se debe hacer luego del ciclo. 

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

Se inicializa la variable que sirve para mantener el ciclo y luego se crean 3 etiquetas: una para evaluar la condición, otra para indicar que se debe hacer si se cumple la condición y otra que indique lo que hay que hacer cuando no se cumple la condición inicial. 
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

- Cada `case` se convierte en una comparación.
- Cada bloque tiene una etiqueta (`L1`, `L2`…).
- El `default` se traduce a un salto directo si no coincide ningún caso.
- Al final se agrega otra etiqueta que marca el final del switch. 

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

- `func` marca el inicio de la función con metadatos (nombre, parámetros, tipo retorno).
- `param` define los parámetros que entran al entorno local.
- `return` indica el valor de retorno.
- `endfunc` marca el fin del bloque de función.

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

- Se empujan los argumentos con `param`.
- Luego se realiza la llamada con `call` indicando la cantidad de parámetros.
- No se almacena retorno, porque no se usa el resultado.

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

- El resultado de la función se guarda en un temporal
- Luego se asigna a la variable.

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

- `class` / `endclass` delimitan la clase.
- `field` indica un atributo de la clase.
- `param this` referencia la instancia actual.
- Los métodos se traducen como funciones con `this` como primer parámetro.

### Ejemplo

Código fuente:
```compiscript
class Animal {
  nombre: string;

  function constructor(nombre: string) {
    this.nombre = nombre;
  }

  function hablar(): string {
    return this.nombre + " hace ruido.";
  }
}
```

TAC:
```tac
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

## Instanciación y métodos

- Para llamar a un método de una clase se usa la instrucción call, se indica la clase y el método que se quiere usar separado por un punto. .
- Luego se puede asignar el resultado a una variable .
- Se sigue el mismo procedimiento para crear un nuevo objeto pero se usa el constructor de la variable.

### Ejemplo

Código fuente:
```compiscript
a = new Animal("Perro");
a.hablar();
```

TAC:
```tac
param "Perro"
call Animal.constructor, 1, t1
a = t1
param a
call Animal.hablar, 1, t2
```

---

## Arreglos

- `alloc n, -, t` → reserva espacio para `n` elementos.
- `[]=` → asigna valor en una posición.
- `[]` → accede al valor almacenado.

### Ejemplo

Código fuente:
```compiscript
arr = [1, 2, 3];
arr[1] = 5;
x = arr[2];
```

TAC:
```tac
alloc 3, -, t1
t1[0] = 1
t1[1] = 2
t1[2] = 3
arr = t1
[]= 5, 1, arr
[] arr, 2, t2
x = t2
```

---

## Excepciones

- `ON_EXCEPTION` → indica el punto de salto en caso de error.
- `EXC_ASSIGN` → vincula el error capturado a una variable (`e`).
- `label Lx_end` marca el final del bloque `try-catch`.

### Ejemplo

Código fuente:
```compiscript
try {
  risky();
} catch (e) {
  print(e);
}
```

TAC:
```tac
label L1_try:
ON_EXCEPTION -> L1_catch
call risky, 0
goto L1_end
label L1_catch:
EXC_ASSIGN "Exception", -, e
print(e)
label L1_end:
```









