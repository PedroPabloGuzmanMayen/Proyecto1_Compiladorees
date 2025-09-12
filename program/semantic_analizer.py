from antlr4 import *
from symbolTable import Symbol_table, Register
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from CompiscriptVisitor import CompiscriptVisitor
import re


class semantic_analyzer(CompiscriptVisitor):

    def __init__(self):
        self.global_table = Symbol_table()
        self.current_table = self.global_table
        self.scope_stack = [self.global_table]
        self.current_class = None
        self.current_function = None
        self.errors = []
        self.in_loop = 0  # Para verificar break/continue
        self.while_scope_counter = 0
        self.for_scope_counter = 0
        self.if_statement_scope_counter = 0

    def add_error(self, ctx, message):
        """Registra un error con número de línea."""
        line = self.get_line_number(ctx)
        self.errors.append(f"ERROR L{line}: {message}")

    def enter_scope(self, scope_name):
        new_table = self.current_table.create_child_scope(scope_name)
        self.current_table = new_table
        self.scope_stack.append(new_table)
        return new_table
    
    def get_line_number(self, ctx):
        return ctx.start.line if ctx.start else 0
    
    def exit_scope(self):
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_table = self.scope_stack[-1]
        return self.current_table
    
    def parse_type(self, type_ctx):
        """Parsea una anotación de tipo y retorna (tipo_base, dimensiones)"""
        if not type_ctx:
            return None, 0
            
        base_type = None
        dimensions = 0
        
        # Obtener tipo base
        if type_ctx.baseType():
            base_type_text = type_ctx.baseType().getText()
            # Mapear tipos de la gramática
            if base_type_text == "integer":
                base_type = "integer"
            elif base_type_text == "boolean":
                base_type = "boolean"
            elif base_type_text == "string":
                base_type = "string"
            else:
                # Es un identificador de clase
                base_type = base_type_text
        
        # Contar dimensiones de array
        dimensions = len(type_ctx.children) - 1 if hasattr(type_ctx, 'children') else 0
        for child in type_ctx.children if hasattr(type_ctx, 'children') else []:
            if child.getText() == "[]":
                dimensions += 1
                
        return base_type, dimensions
    
    def infer_expression_type(self, ctx):
        """Infiere el tipo de una expresión de forma lexemática y segura."""
        if not ctx:
            return None

        text = ctx.getText()

        # Literales primarios
        if re.fullmatch(r"\d+", text):
            return "integer"
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            return "string"
        if text in ("true", "false"):
            return "boolean"
        if text == "null":
            return "null"

        # Arreglo literal (detección superficial).
        # Nota: puedes mejorar esto luego para inferir tipo de elementos.
        if text.startswith("[") and text.endswith("]"):
            return "array", {}

        # Identificador simple → consulta en la tabla de símbolos
        if re.fullmatch(r"[A-Za-z_]\w*", text):
            symbol = self.current_table.lookup_global(text)
            if symbol:
                return symbol.type  # p.ej., "integer" o "string"

        # Expresiones compuestas (e.g., a+b) o casos no contemplados
        return None

    def handle_array_elements_type(self):
        pass

    # Visit a parse tree produced by CompiscriptParser#program.
    def visitProgram(self, ctx:CompiscriptParser.ProgramContext):
        """Visita el programa principal"""
        for statement in ctx.statement():
            self.visit(statement)
        return None
    
    def visitBinaryExpr(self, ctx):
        left_type = self.infer_expression_type(ctx.left)
        right_type = self.infer_expression_type(ctx.right)
        op = ctx.op.text
    
        # Casos aritméticos
        if op in ["+", "-", "*", "/", "%"]:
            if left_type != "integer" or right_type != "integer":
                self.add_error(ctx, f"Operador {op} solo válido para enteros, no {left_type} y {right_type}")
            return "integer"
        # Comparaciones (devuelven boolean)
        if op in ["<", "<=", ">", ">="]:
            if left_type != "integer" or right_type != "integer":
                self.add_error(ctx, f"Comparación {op} solo válida para enteros")
            return "boolean"
        # Igualdad 
        if op in ["==", "!="]:
            if left_type != right_type:
                self.add_error(ctx, f"No se puede comparar {left_type} con {right_type}")
            return "boolean"
        # Booleanos
        if op in ["&&", "||"]:
            if left_type != "boolean" or right_type != "boolean":
                self.add_error(ctx, f"Operador {op} solo válido para booleanos, no {left_type} y {right_type}")
            return "boolean"
        return None
    
    #Visit a parse tree produced by CompiscriptParser#block
    def visitBlock(self, ctx:CompiscriptParser.BlockContext):
        """Visita un bloque de código"""
        for statement in ctx.statement():
            self.visit(statement)
        return None


    # Visit a parse tree produced by CompiscriptParser#variableDeclaration.
    def visitVariableDeclaration(self, ctx):
        """Visita un nodo que declara una variable"""
        var_name = ctx.Identifier().getText()
        line_num = self.get_line_number(ctx)

        if not ctx.typeAnnotation():
            raise Exception(f"ERROR: la variable '{var_name}' debe tener tipo explícito")

        var_type, dimensions = self.parse_type(ctx.typeAnnotation().type_())

        if ctx.initializer():
            inferred_type = self.infer_expression_type(ctx.initializer().expression())
            self.visit(ctx.initializer().expression())

            if inferred_type == "array" and dimensions != 0:
                pass
            if var_type != inferred_type:
                raise Exception(f"ERROR: inicializador '{inferred_type}' incompatible con tipo '{var_type}'")

        if not self.current_table.insert_symbol(
            identifier=var_name,
            type=var_type,
            scope = self.current_table.scope,
            line_pos=line_num,
            is_mutable=True,
            kind="variable",
            params =[],
            return_type = None,
            parent_class= None,
            dim=dimensions
        ):
            raise Exception(f"ERROR:Variable '{var_name}' ya declarada en este ámbito")


    # Visit a parse tree produced by CompiscriptParser#constantDeclaration.
    def visitConstantDeclaration(self, ctx:CompiscriptParser.ConstantDeclarationContext):
        """Visita definiciones de constantes  """
    
        var_name = ctx.Identifier().getText()
        line_num = self.get_line_number(ctx)

        if not ctx.typeAnnotation():
            raise Exception(f"ERROR: la variable '{var_name}' debe tener tipo explícito")

        var_type, dimensions = self.parse_type(ctx.typeAnnotation().type_())

        if not ctx.expression():
            raise Exception(f"ERROR: para declarar una constante debes siempre especificar un valor inicial")


        inferred_type = self.infer_expression_type(ctx.expression())
       

        if inferred_type == "array" and dimensions != 0:
            pass
        if var_type != inferred_type:
            raise Exception(f"ERROR: inicializador '{inferred_type}' incompatible con tipo '{var_type}'")

        if not self.current_table.insert_symbol(
            identifier=var_name,
            type=var_type,
            scope = self.current_table.scope,
            line_pos=line_num,
            is_mutable=False,
            kind="variable",
            params =[],
            return_type = None,
            parent_class= None,
            dim=dimensions
        ):
            raise Exception(f"ERROR:Variable '{var_name}' ya declarada en este ámbito")
            

    def visitIfStatement(self, ctx:CompiscriptParser.IfStatementContext):
        """Verifica la condición del if y visita los bloques (if y optional else)."""
        cond_ctx = ctx.expression()
        cond_type = self.infer_expression_type(cond_ctx)
        if cond_type is None:
            self.add_error(ctx, f"No se pudo inferir tipo de la condición del if")
        elif cond_type != "boolean":
            self.add_error(ctx, f"Condición de if debe ser boolean (obtenido: {cond_type})")

        # El bloque 'if' es el primer block
        if getattr(ctx, "block", None):
            # ctx.block(0) -> bloque del if, ctx.block(1) -> else (si existe)
            if ctx.block(0):
                self.visit(ctx.block(0))
            if len(ctx.block()) > 1 and ctx.block(1):
                self.visit(ctx.block(1))
        return None

    def visitTryCatchStatement(self, ctx:CompiscriptParser.TryCatchStatementContext):
        """
        Estructura de la regla 'try' block 'catch' '(' Identifier ')' block
        """
        try:
            # visitar try block en su propio scope opcional 
            if ctx.block(0):
                self.enter_scope(f"try_{self.get_line_number(ctx)}")
                self.visit(ctx.block(0))
                self.exit_scope()

            # catch: declarar identificador en un nuevo scope
            # el identificador token está como ctx.Identifier()
            catch_id = None
            # localizar el identificador: que está después de 'catch' '(' Identifier ')'
            if ctx.Identifier():
                catch_id = ctx.Identifier().getText()
            else:
                # fallback: intentar obtener de children
                for ch in ctx.children:
                    if hasattr(ch, 'getText') and re.fullmatch(r"[A-Za-z_]\w*", ch.getText()):
                        catch_id = ch.getText()
                        break

            # crear scope del catch y declarar la variable del catch
            self.enter_scope(f"catch_{self.get_line_number(ctx)}")
            if catch_id:
                inserted = self.current_table.insert_symbol(
                    identifier=catch_id,
                    type="exception",
                    scope=self.current_table.scope,
                    line_pos=self.get_line_number(ctx),
                    is_mutable=False,
                    kind="variable",
                    params=[],
                    return_type=None,
                    parent_class=None,
                    dim=0
                )
                if not inserted:
                    self.add_error(ctx, f"Identificador de catch '{catch_id}' ya declarado en este ámbito")

            # visitar el bloque del catch 
            if len(ctx.block()) > 1:
                self.visit(ctx.block(1))
            else:
                for b in ctx.block():
                    self.visit(b)

            # salir del scope de catch
            self.exit_scope()

        except Exception as e:
            self.add_error(ctx, str(e))
        return None

    def visitSwitchStatement(self, ctx:CompiscriptParser.SwitchStatementContext):
        """
        Verifica que cada case sea compatible con la expresión del switch y que no haya case duplicados
        """
        try:
            switch_expr = ctx.expression()
            switch_type = self.infer_expression_type(switch_expr)
            if switch_type is None:
                self.add_error(ctx, "No se pudo inferir tipo de la expresión del switch")

            seen_cases = set()
            # ctx.switchCase() # devuelve lista de case contexts
            for case_ctx in list(ctx.switchCase()):
                case_expr = case_ctx.expression()
                case_type = self.infer_expression_type(case_expr)
                if switch_type and case_type and (case_type != switch_type):
                    self.add_error(case_ctx, f"Case de tipo {case_type} incompatible con switch de tipo {switch_type}")
                case_text = case_expr.getText()
                if case_text in seen_cases:
                    self.add_error(case_ctx, f"Case duplicado: {case_text}")
                else:
                    seen_cases.add(case_text)

                for st in case_ctx.statement():
                    self.visit(st)

            # default 
            if ctx.defaultCase():
                # defaultCase: visit its statements
                for st in ctx.defaultCase().statement():
                    self.visit(st)
        except Exception as e:
            self.add_error(ctx, str(e))
        return None

    def visitAssignment(self, ctx:CompiscriptParser.AssignmentContext):
        """
        Maneja asignaciones en sentencia
        """
        try:
            # Detectar si es property assignment
            if ctx.getChildCount() >= 2 and ctx.getChild(1).getText() == '.':
                # expression '.' Identifier '=' expression ';'
                left_expr = ctx.expression(0)
                prop_name = ctx.Identifier().getText()
                right_expr = ctx.expression(1)

                left_text = left_expr.getText()
                symbol = self.current_table.lookup_global(left_text)
                if not symbol:
                    self.add_error(ctx, f"Asigna propiedad en objeto no declarado '{left_text}'")
                self.visit(left_expr)
                self.visit(right_expr)
                return None

            else:
                # Identifier '=' expression ';'
                var_name = ctx.Identifier().getText()
                rhs = ctx.expression(0)
                symbol = self.current_table.lookup_global(var_name)
                if not symbol:
                    self.add_error(ctx, f"Asignación a variable no declarada '{var_name}'")
                    self.visit(rhs)
                    return None

                # verificar mutabilidad 
                is_mutable = getattr(symbol, 'is_mutable', None)
                if is_mutable is None:
                    is_mutable = getattr(symbol, 'mutable', True)

                if not is_mutable:
                    self.add_error(ctx, f"Intento de asignar a constante/variable no mutable '{var_name}'")

                inferred = self.infer_expression_type(rhs)
                if inferred is None:
                    self.visit(rhs)
                    self.add_error(ctx, f"No se pudo inferir tipo del lado derecho en la asignación a '{var_name}'")
                    return None

                var_type = getattr(symbol, 'type', None)
                var_dim = getattr(symbol, 'dim', 0)

                if inferred == "array":
                    if not var_dim or var_dim == 0:
                        self.add_error(ctx, f"Asigna un array a '{var_name}' no declarado como array")
                else:
                    if var_type and (inferred != var_type):
                        self.add_error(ctx, f"Tipo incompatible en asignación a '{var_name}': {inferred} vs {var_type}")

                self.visit(rhs)
                return None

        except Exception as e:
            self.add_error(ctx, str(e))
            return None

    def visitAssignExpr(self, ctx:CompiscriptParser.AssignExprContext):
        """
        assignmentExpr: lhs=leftHandSide '=' assignmentExpr
        """
        try:
            lhs = ctx.lhs  
            rhs = ctx.assignmentExpr()
            lhs_text = lhs.getText()
            if re.fullmatch(r"[A-Za-z_]\w*", lhs_text):
                symbol = self.current_table.lookup_global(lhs_text)
                if not symbol:
                    self.add_error(ctx, f"Asignación en expresión a variable no declarada '{lhs_text}'")
                else:
                    if not getattr(symbol, 'is_mutable', True):
                        self.add_error(ctx, f"Asignación a no mutable '{lhs_text}'")
                    inferred = self.infer_expression_type(rhs)
                    var_type = getattr(symbol, 'type', None)
                    var_dim = getattr(symbol, 'dim', 0)
                    if inferred == "array":
                        if not var_dim:
                            self.add_error(ctx, f"Asigna array a '{lhs_text}' no declarado como array")
                    else:
                        if var_type and inferred and (inferred != var_type):
                            self.add_error(ctx, f"Tipo incompatible en asignación a '{lhs_text}': {inferred} vs {var_type}")
            self.visitChildren(ctx)
        except Exception as e:
            self.add_error(ctx, str(e))
        return None

    def visitPropertyAssignExpr(self, ctx:CompiscriptParser.PropertyAssignExprContext):
        # expression '.' Identifier '=' assignmentExpr
        try:
            left = ctx.lhs 
            self.visitChildren(ctx)
            # Si left es identificador, verificar que exista
            left_text = left.getText() if left is not None else None
            if left_text and re.fullmatch(r"[A-Za-z_]\w*", left_text):
                sym = self.current_table.lookup_global(left_text)
                if not sym:
                    self.add_error(ctx, f"Asigna propiedad en objeto no declarado '{left_text}'")
        except Exception as e:
            self.add_error(ctx, str(e))
        return None

    def visitWhileStatement(self, ctx:CompiscriptParser.WhileStatementContext):
        """Verifica la condición del while y marca que estamos dentro de un bucle."""
        cond_ctx = ctx.expression()
        cond_type = self.infer_expression_type(cond_ctx)
        if cond_type is None:
            self.add_error(ctx, f"No se pudo inferir tipo de la condición del while")
        elif cond_type != "boolean":
            self.add_error(ctx, f"Condición de while debe ser boolean (obtenido: {cond_type})")

        self.in_loop += 1
        # visitar el bloque del while 
        if ctx.block():
            self.visit(ctx.block())
        self.in_loop -= 1
        return None

    def visitDoWhileStatement(self, ctx:CompiscriptParser.DoWhileStatementContext):
        """Visita el bloque do y luego verifica la condición del while."""
        self.in_loop += 1
        if ctx.block():
            self.visit(ctx.block())

        cond_ctx = ctx.expression()
        cond_type = self.infer_expression_type(cond_ctx)
        if cond_type is None:
            self.add_error(ctx, f"No se pudo inferir tipo de la condición del do-while")
        elif cond_type != "boolean":
            self.add_error(ctx, f"Condición de do-while debe ser boolean (obtenido: {cond_type})")

        self.in_loop -= 1
        return None

    def visitForStatement(self, ctx:CompiscriptParser.ForStatementContext):
        """
        Crea un scope para el for, verifica condición (si existe) y marca que estamos en bucle.
        """
        self.enter_scope(f"for_{self.get_line_number(ctx)}")

        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())

        exprs = list(ctx.expression()) if ctx.expression() else []
        cond = exprs[0] if len(exprs) >= 1 else None
        incr = exprs[1] if len(exprs) >= 2 else None

        if cond is not None:
            cond_type = self.infer_expression_type(cond)
            if cond_type is None:
                self.add_error(ctx, "No se pudo inferir tipo de la condición del for")
            elif cond_type != "boolean":
                self.add_error(ctx, f"Condición de for debe ser boolean (obtenido: {cond_type})")

        if incr is not None:
            self.visit(incr)

        self.in_loop += 1
        if ctx.block():
            self.visit(ctx.block())
        self.in_loop -= 1

        self.exit_scope()
        return None


    # Visit a parse tree produced by CompiscriptParser#typeAnnotation.
    def visitTypeAnnotation(self, ctx:CompiscriptParser.TypeAnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#initializer.
    def visitInitializer(self, ctx:CompiscriptParser.InitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#assignment.
    def visitAssignment(self, ctx:CompiscriptParser.AssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#expressionStatement.
    def visitExpressionStatement(self, ctx:CompiscriptParser.ExpressionStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#printStatement.
    def visitPrintStatement(self, ctx:CompiscriptParser.PrintStatementContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CompiscriptParser#whileStatement.
    def visitWhileStatement(self, ctx:CompiscriptParser.WhileStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#foreachStatement.
    def visitForeachStatement(self, ctx:CompiscriptParser.ForeachStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#breakStatement.
    def visitBreakStatement(self, ctx:CompiscriptParser.BreakStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#continueStatement.
    def visitContinueStatement(self, ctx:CompiscriptParser.ContinueStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#returnStatement.
    def visitReturnStatement(self, ctx:CompiscriptParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#switchCase.
    def visitSwitchCase(self, ctx:CompiscriptParser.SwitchCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#defaultCase.
    def visitDefaultCase(self, ctx:CompiscriptParser.DefaultCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#functionDeclaration.
    def visitFunctionDeclaration(self, ctx):
        """Verifica declaraciones de funciones"""

        func_name = ctx.Identifier().getText()
        line_num = self.get_line_number(ctx)
        
        # Procesar parámetros
        params = []
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                param_name = param_ctx.Identifier().getText()
                param_type = None
                if param_ctx.type():
                    param_type, _ = self.parse_type(param_ctx.type())
                params.append({"name": param_name, "type": param_type})

        if ctx.type_(): #Verificar si el usuario definio un tipo 
            function_return_type = self.parse_type(ctx.type_)
        
        # Declarar la función en el ámbito actual
        if not self.current_table.insert_symbol(
            lidentifier=func_name,
            type=var_type,
            scope = self.current_table.scope,
            line_pos=line_num,
            is_mutable=False,
            kind="function",
            params =[],
            return_type = None,
            parent_class= None,
            dim=dimensions
        ):
            raise Exception("ERROR: redeclaración de función")
        
        # Entrar al ámbito de la función  b
        self.enter_scope(f"function_{func_name}")
        old_function = self.current_function
        self.current_function = func_name
        
        # Declarar parámetros como variables locales
        for param in params:
            try:
                self.current_table.insert_symbol(
                    lexeme=param["name"],
                    identifier=param["name"],
                    type=param["type"],
                    line_pos=line_num,
                    kind="parameter"
                )
            except:
                self.add_error(ctx, f"Parámetro '{param['name']}' duplicado")
        
        # Visitar el cuerpo de la función
        if ctx.block():
            self.visit(ctx.block())
        
        # Salir del ámbito
        self.current_function = old_function
        self.exit_scope()

    # Visit a parse tree produced by CompiscriptParser#parameters.
    def visitParameters(self, ctx:CompiscriptParser.ParametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#parameter.
    def visitParameter(self, ctx:CompiscriptParser.ParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#classDeclaration.
    def visitClassDeclaration(self, ctx:CompiscriptParser.ClassDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#classMember.
    def visitClassMember(self, ctx:CompiscriptParser.ClassMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#expression.
    def visitExpression(self, ctx:CompiscriptParser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#AssignExpr.
    def visitAssignExpr(self, ctx:CompiscriptParser.AssignExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#PropertyAssignExpr.
    def visitPropertyAssignExpr(self, ctx:CompiscriptParser.PropertyAssignExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#ExprNoAssign.
    def visitExprNoAssign(self, ctx:CompiscriptParser.ExprNoAssignContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#TernaryExpr.
    def visitTernaryExpr(self, ctx:CompiscriptParser.TernaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#logicalOrExpr.
    def visitLogicalOrExpr(self, ctx:CompiscriptParser.LogicalOrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#logicalAndExpr.
    def visitLogicalAndExpr(self, ctx:CompiscriptParser.LogicalAndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#equalityExpr.
    def visitEqualityExpr(self, ctx:CompiscriptParser.EqualityExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#relationalExpr.
    def visitRelationalExpr(self, ctx:CompiscriptParser.RelationalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#additiveExpr.
    def visitAdditiveExpr(self, ctx:CompiscriptParser.AdditiveExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#multiplicativeExpr.
    def visitMultiplicativeExpr(self, ctx:CompiscriptParser.MultiplicativeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#unaryExpr.
    def visitUnaryExpr(self, ctx:CompiscriptParser.UnaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#primaryExpr.
    def visitPrimaryExpr(self, ctx:CompiscriptParser.PrimaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#literalExpr.
    def visitLiteralExpr(self, ctx:CompiscriptParser.LiteralExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#leftHandSide.
    def visitLeftHandSide(self, ctx:CompiscriptParser.LeftHandSideContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#IdentifierExpr.
    def visitIdentifierExpr(self, ctx:CompiscriptParser.IdentifierExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#NewExpr.
    def visitNewExpr(self, ctx:CompiscriptParser.NewExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#ThisExpr.
    def visitThisExpr(self, ctx:CompiscriptParser.ThisExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#CallExpr.
    def visitCallExpr(self, ctx:CompiscriptParser.CallExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#IndexExpr.
    def visitIndexExpr(self, ctx:CompiscriptParser.IndexExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#PropertyAccessExpr.
    def visitPropertyAccessExpr(self, ctx:CompiscriptParser.PropertyAccessExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#arguments.
    def visitArguments(self, ctx:CompiscriptParser.ArgumentsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#arrayLiteral.
    def visitArrayLiteral(self, ctx:CompiscriptParser.ArrayLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#type.
    def visitType(self, ctx:CompiscriptParser.TypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#baseType.
    def visitBaseType(self, ctx:CompiscriptParser.BaseTypeContext):
        return self.visitChildren(ctx)



del CompiscriptParser
