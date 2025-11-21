.data
.text
.globl _start
_start:
# No main(): ejecutando código global directamente
li $t0, 0
move $t1, $t0
# WARN: variable i sólo en registro $t1 (no se guarda en memoria)
L1_start:
# WARN: variable i usada sólo en registro $t1
li $t2, 5
slt $t3, $t1, $t2
bne $t3, $zero, L1_body
j L1_after
L1_body:
# WARN: variable i usada sólo en registro $t1
move $a0, $t1
li $v0, 1
syscall
li $v0, 11
li $a0, 10
syscall
L1_update:
# WARN: variable i usada sólo en registro $t1
li $t4, 1
add $t5, $t1, $t4
move $t1, $t5
# WARN: variable i sólo en registro $t1 (no se guarda en memoria)
j L1_start
L1_after:
li $v0, 10
syscall
