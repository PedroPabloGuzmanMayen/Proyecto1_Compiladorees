.data
.text
.globl main
.globl _start
_start:
jal main
li $v0, 10
syscall
main:
addi $sp, $sp, -8
sw $ra, 0($sp)
sw $fp, 4($sp)
addi $fp, $sp, 4
li $t0, 0
sw $t0, 0($fp)
L1_start:
lw $t1, 0($fp)
li $t2, 3
slt $t3, $t1, $t2
bne $t3, $zero, L1_body
j L1_after
L1_body:
lw $t1, 0($fp)
move $a0, $t1
li $v0, 1
syscall
li $v0, 11
li $a0, 10
syscall
L1_update:
lw $t1, 0($fp)
li $t4, 1
add $t5, $t1, $t4
sw $t5, 0($fp)
j L1_start
L1_after:
lw $ra, -4($fp)
lw $fp, 0($fp)
addi $sp, $fp, -4
jr $ra
