addi $sp, $sp, -288
# reserva 288 bytes para variables y spills
li $t0, 1
li $t1, 2
add $t2, $t0, $t1
sw $t2, 0($sp)
li $t3, 3
li $t4, 4
add $t2, $t3, $t4
sw $t2, 0($sp)
li $t5, 5
li $t6, 6
add $t2, $t5, $t6
sw $t2, 0($sp)
li $t7, 7
li $t8, 8
add $t2, $t7, $t8
sw $t2, 0($sp)
li $t9, 9
li $s0, 10
add $t2, $t9, $s0
sw $t2, 0($sp)
li $s1, 11
li $s2, 12
add $t2, $s1, $s2
sw $t2, 0($sp)
li $s3, 13
li $s4, 14
add $t2, $s3, $s4
sw $t2, 0($sp)
li $s5, 15
li $s6, 16
add $t2, $s5, $s6
sw $t2, 0($sp)
li $s7, 17
li $t0, 18
add $t2, $s7, $t0
sw $t2, 0($sp)
li $t1, 19
li $t3, 20
add $t2, $t1, $t3
sw $t2, 0($sp)
li $t4, 21
li $t5, 22
add $t2, $t4, $t5
sw $t2, 0($sp)
li $t6, 23
li $t7, 24
add $t2, $t6, $t7
sw $t2, 0($sp)
li $t8, 25
li $t9, 26
add $t2, $t8, $t9
sw $t2, 0($sp)
li $s0, 27
li $s1, 28
add $t2, $s0, $s1
sw $t2, 0($sp)
li $s2, 29
li $s3, 30
add $t2, $s2, $s3
sw $t2, 0($sp)
li $s4, 31
li $s5, 32
add $t2, $s4, $s5
sw $t2, 0($sp)
li $s6, 33
li $s7, 34
add $t2, $s6, $s7
sw $t2, 0($sp)
li $t0, 35
li $t1, 36
add $t2, $t0, $t1
sw $t2, 0($sp)
li $t3, 37
li $t4, 38
add $t2, $t3, $t4
sw $t2, 0($sp)
li $t5, 39
li $t6, 40
add $t2, $t5, $t6
sw $t2, 0($sp)
li $t7, 41
li $t8, 42
add $t2, $t7, $t8
sw $t2, 0($sp)
li $t9, 43
li $s0, 44
add $t2, $t9, $s0
sw $t2, 0($sp)
li $s1, 45
li $s2, 46
add $t2, $s1, $s2
sw $t2, 0($sp)
li $s3, 47
li $s4, 48
add $t2, $s3, $s4
sw $t2, 0($sp)
li $s5, 49
li $s6, 50
add $t2, $s5, $s6
sw $t2, 0($sp)
li $s7, 51
li $t0, 52
add $t2, $s7, $t0
sw $t2, 0($sp)
lw $t1, 0($sp)
lw $t3, 0($sp)
add $t2, $t1, $t3
lw $t4, 0($sp)
add $t5, $t2, $t4
lw $t6, 0($sp)
add $t7, $t5, $t6
lw $t8, 0($sp)
add $t9, $t7, $t8
lw $s0, 0($sp)
add $s1, $t9, $s0
lw $s2, 0($sp)
add $s3, $s1, $s2
lw $s4, 0($sp)
add $s5, $s3, $s4
lw $s6, 0($sp)
add $s7, $s5, $s6
lw $t0, 0($sp)
add $t1, $s7, $t0
lw $t3, 0($sp)
add $t2, $t1, $t3
lw $t4, 0($sp)
add $t5, $t2, $t4
lw $t6, 0($sp)
add $t7, $t5, $t6
lw $t8, 0($sp)
add $t9, $t7, $t8
lw $s0, 0($sp)
add $s1, $t9, $s0
lw $s2, 0($sp)
add $s3, $s1, $s2
lw $s4, 0($sp)
add $s5, $s3, $s4
lw $s6, 0($sp)
add $s7, $s5, $s6
lw $t0, 0($sp)
add $t1, $s7, $t0
lw $t3, 0($sp)
add $t2, $t1, $t3
lw $t4, 0($sp)
add $t5, $t2, $t4
lw $t6, 0($sp)
add $t7, $t5, $t6
lw $t8, 0($sp)
add $t9, $t7, $t8
lw $s0, 0($sp)
add $s1, $t9, $s0
lw $s2, 0($sp)
add $s3, $s1, $s2
lw $s4, 0($sp)
add $s5, $s3, $s4
sw $s5, 0($sp)
lw $s6, 0($sp)
move $a0, $s6
li $v0, 1
syscall
addi $sp, $sp, 288
