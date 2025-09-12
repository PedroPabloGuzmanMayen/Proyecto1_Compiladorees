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

    def add_error(self, ctx, message):
        """Registra un error con número de línea."""
        line = self.get_line_number(ctx)
        self.errors.append(f"ERROR L{line}: {message}")

    def _set_inferred(self, ctx, base, dim=0):
        setattr(ctx, "_type_base", base)
        setattr(ctx, "_type_dim", dim)
        return base, dim

    def _get_inferred(self, ctx):
        return getattr(ctx, "_type_base", None), getattr(ctx, "_type_dim", 0)

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
        if not type_ctx:
            return None, 0
        text = type_ctx.getText()         
        dim = text.count('[]')
        base = text.replace('[]','')
        return base, dim

    def infer_expression_type(self, ctx):
        """Infiere el tipo de una expresión"""
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

        if text.startswith("[") and text.endswith("]"):
            return "array", {}

        if re.fullmatch(r"[A-Za-z_]\w*", text):
            symbol = self.current_table.lookup_global(text)
            if symbol:
                return symbol.type 


        return None

    def infer_type_and_dim(self, expr_ctx):
   
        b, d = self._get_inferred(expr_ctx)
        if b is not None or d != 0:
            return b, d

        try:
            self.visit(expr_ctx)
            b, d = self._get_inferred(expr_ctx)
            if b is not None or d != 0:
                return b, d
        except Exception:
            pass


        text = expr_ctx.getText()
        if re.fullmatch(r"\d+", text):                 return "integer", 0
        if text in ("true","false"):                   return "boolean", 0
        if len(text)>=2 and text[0]=='"' and text[-1]=='"':  return "string", 0
        if text == "null":                             return "null", 0

        if text.startswith('[') and text.endswith(']'):
        
            base, dim = self._infer_array_from_text(text)
            return base, dim


        if re.fullmatch(r"[A-Za-z_]\w*", text):
            sym = self.current_table.lookup_global(text)
            if sym:
                return getattr(sym,'type',None), getattr(sym,'dim',0)

        if re.fullmatch(r"[A-Za-z0-9_\s+\-*/%()]+", text) and '"' not in text:
            tokens = re.split(r"[+\-*/%()]", text)
            tokens = [t.strip() for t in tokens if t.strip()]
            all_int = True
            for t in tokens:
                if t.isdigit():
                    continue
                if re.fullmatch(r"[A-Za-z_]\w*", t):
                    sym = self.current_table.lookup_global(t)
                    if not sym or getattr(sym, 'type', None) != 'integer' or getattr(sym,'dim',0)!=0:
                        all_int = False; break
                else:
                    all_int = False; break
            if all_int:
                return "integer", 0

        return None, 0

    def _infer_array_from_text(self, text):
        # parse top-level commas con balanceo de corchetes
        assert text[0]=='[' and text[-1]==']'
        inner = text[1:-1].strip()
        if not inner:
            return None, 1

        parts = []
        buf, depth = "", 0
        for ch in inner:
            if ch == '[': depth += 1
            if ch == ']': depth -= 1
            if ch == ',' and depth == 0:
                parts.append(buf.strip()); buf = ""
            else:
                buf += ch
        if buf.strip():
            parts.append(buf.strip())

        bases, dims = [], []
        for p in parts:
            if p.startswith('[') and p.endswith(']'):
                b, d = self._infer_array_from_text(p)
            elif p.isdigit():
                b, d = "integer", 0
            elif p in ("true","false"):
                b, d = "boolean", 0
            elif len(p)>=2 and p[0]=='"' and p[-1]=='"':
                b, d = "string", 0
            else:
                # identificador: mira tabla
                if re.fullmatch(r"[A-Za-z_]\w*", p):
                    sym = self.current_table.lookup_global(p)
                    b, d = (getattr(sym,'type',None), getattr(sym,'dim',0)) if sym else (None,0)
                else:
                    b, d = None, 0
            bases.append(b); dims.append(d)

        known = [b for b in bases if b is not None]
        base = known[0] if known and all(k == known[0] for k in known) else None
        dim = 1 + (dims[0] if dims else 0)
        return base, dim


    def _analyze_array_literal(self, ctx):
        """
        Analiza arrays
        """
        al = None
        if hasattr(ctx, "arrayLiteral") and ctx.arrayLiteral():
            al = ctx.arrayLiteral()
        elif hasattr(ctx, "primaryExpr") and ctx.primaryExpr():
            pe = ctx.primaryExpr()
            if hasattr(pe, "literalExpr") and pe.literalExpr() and pe.literalExpr().arrayLiteral():
                al = pe.literalExpr().arrayLiteral()
        elif hasattr(ctx, "literalExpr") and ctx.literalExpr() and ctx.literalExpr().arrayLiteral():
            al = ctx.literalExpr().arrayLiteral()

        elems = list(al.expression()) if al else []

 
        if not elems:
            txt = ctx.getText()
            if txt == "[]":
                return None, 1 

            return None, 1

        bases, dims = [], []
        for e in elems:
            b, d = self.infer_type_and_dim(e)
            bases.append(b); dims.append(d)

        known = [b for b in bases if b is not None]
        if known and any(b != known[0] for b in known):
            self.add_error(ctx, f"Literal de arreglo heterogéneo: {set(known)}")

        if any(d != dims[0] for d in dims):
            self.add_error(ctx, "Arreglo no rectangular")

        return (known[0] if known else None), 1 + (dims[0] if dims else 0)


    # Visit a parse tree produced by CompiscriptParser#program.
    def visitProgram(self, ctx:CompiscriptParser.ProgramContext):
        """Visita el programa principal"""
        for statement in ctx.statement():
            self.visit(statement)
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
            self.add_error(ctx, f"La variable '{var_name}' debe tener tipo explícito")

        var_type, dimensions = self.parse_type(ctx.typeAnnotation().type_())

        if ctx.initializer():
            inferred_type, inferred_dim = self.infer_type_and_dim(ctx.initializer().expression())

            if inferred_type is None and inferred_dim > 0:
                inferred_type = var_type

            if var_type and var_type != inferred_type:
                self.add_error(ctx, f"Tipo incompatible: {var_type} vs {inferred_type}")
            if dimensions and dimensions != inferred_dim:
                self.add_error(ctx, f"Dimensión incompatible: {var_type} vs {inferred_dim}")
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
            self.add_error(ctx, f"Variable {var_name} ya declarada!")


    # Visit a parse tree produced by CompiscriptParser#constantDeclaration.
    def visitConstantDeclaration(self, ctx):
        """Define la declaracióon de una constante"""
        name = ctx.Identifier().getText()
        line = self.get_line_number(ctx)

        decl_base, decl_dim = (None, 0)
        if ctx.typeAnnotation():
            decl_base, decl_dim = self.parse_type(ctx.typeAnnotation().type_())

        if ctx.expression() is None:

            self.add_error(ctx, f"Constante '{name}' requiere '= expresión'")
            expr_base, expr_dim = (None, 0)
        else:
            expr_base, expr_dim = self.infer_type_and_dim(ctx.expression())

            if expr_base is None and expr_dim > 0 and decl_base is not None:
                expr_base = decl_base

        if decl_base is not None and expr_base is not None and decl_base != expr_base:
            self.add_error(ctx, f"Tipo incompatible: {decl_base} vs {expr_base}")
        if decl_dim and decl_dim != expr_dim:
            self.add_error(ctx, f"Dimensión incompatible: {decl_dim} vs {expr_dim}")

        if not self.current_table.insert_symbol(
            identifier=name,
            type=decl_base,
            scope=self.current_table.scope,
            line_pos=line,
            is_mutable=False,
            kind="variable",
            params=[],
            return_type=None,
            parent_class=None,
            dim=decl_dim
        ):
            self.add_error(ctx, f"Constante {name} ya declarada!")

            

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


    # Visit a parse tree produced by CompiscriptParser#foreachStatement.
    def visitForeachStatement(self, ctx:CompiscriptParser.ForeachStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#breakStatement.
    def visitBreakStatement(self, ctx:CompiscriptParser.BreakStatementContext):
        if self.in_loop == 0:
            self.add_error(ctx, "Solo puedes usar break si estas en un ciclo while o for")
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#continueStatement.
    def visitContinueStatement(self, ctx:CompiscriptParser.ContinueStatementContext):
        if self.in_loop == 0:
            self.add_error(ctx, "Solo puedes usar break si estas en un ciclo while o for")
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#returnStatement.
    def visitReturnStatement(self, ctx):
        if ctx.expression():
            return_type, return_dim = self.infer_type_and_dim(ctx.expression())
        else:
            return_type, return_dim = None, 0

        if self.expected_return_type is None and ctx.expression():
            self.add_error(ctx, "La función es void pero hay un valor en return")

        if self.expected_return_type is not None:
            if return_type != self.expected_return_type:
                self.add_error(ctx, f"Tipo de retorno esperado {self.expected_return_type} y recibido {return_type}")
            if return_dim != (self.expected_dim or 0):
                self.add_error(ctx, f"Dimensión de retorno esperada {self.expected_dim} y recibida {return_dim}")

        self.found_return = True



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
        function_return_type = None
        function_return_dim = None
        
        # Procesar parámetros
        params = []
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                param_name = param_ctx.Identifier().getText()
                param_type = None
                if param_ctx.type_():
                    param_type, param_dimension = self.parse_type(param_ctx.type_())
                params.append({"name": param_name, "type": param_type, "dimension": param_dimension})

        if ctx.type_(): #Verificar si el usuario definio un tipo (Nota: los voids deberán declararse sin un tipo)
            function_return_type, function_return_dim = self.parse_type(ctx.type_())

        if function_return_type not in ["integer", "string", "boolean", None]: #Hay que chequear si es un primitivo, si no tal vez sea una clase
            if not self.current_table.lookup_global(function_return_type):
                self.add_error(ctx, f"El tipo de la función {function_return_type} es inválido, no es un primitivo y tampoco pertence a una clase definida antes")


        # Declarar la función en el ámbito actual
        if not self.current_table.insert_symbol(
            identifier=func_name,
            type=function_return_type,
            scope = self.current_table.scope,
            line_pos=line_num,
            is_mutable=False,
            kind="function",
            params =params,
            return_type = True,
            parent_class= None,
            dim=0
        ):
            self.add_error(ctx, f"Redeclaración de la función {func_name}")
        
        # Entrar al ámbito de la función
        self.enter_scope(f"function_{func_name}")
        old_function = self.current_function
        self.current_function = func_name
        self.found_return = False
        self.expected_return_type = function_return_type
        self.expected_dim = function_return_dim
        
        # Declarar parámetros como variables locales
        for param in params:
            
            if not self.current_table.insert_symbol(
            identifier=param["name"],
            type=param["type"],
            scope = self.current_table.scope,
            line_pos=line_num,
            is_mutable=False,
            kind="variable",
            params =None,
            return_type = None,
            parent_class= None,
            dim=param["dimension"]
            ):
                self.add_error(ctx, f"Parámetro '{param['name']}' duplicado")

        if self.current_class != None and func_name == self.current_class: #Si se cumple esto, significa que la clase tiene contructor
            self.has_constructor = True
            self.constructor_params = params
        
        # Visitar el cuerpo de la función
        if ctx.block():
            self.visit(ctx.block())
        
        # Salir del ámbito
        self.current_function = old_function
        self.exit_scope()

        if self.expected_return_type != None and not self.found_return:
            self.add_error(ctx, f"La función no es void y se esperaba un retorno ")

    # Visit a parse tree produced by CompiscriptParser#parameters.
    def visitParameters(self, ctx:CompiscriptParser.ParametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#parameter.
    def visitParameter(self, ctx:CompiscriptParser.ParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#classDeclaration.
    def visitClassDeclaration(self, ctx:CompiscriptParser.ClassDeclarationContext):
        """Verifica delcaración de clases"""
        ids = ctx.Identifier()               
        class_name = ids[0].getText()
        parent_class_name  = ids[1].getText() if len(ids) > 1 else None
        line_num = self.get_line_number(ctx)

        if not self.current_table.insert_symbol(
            identifier=class_name,
            type=None,
            scope = self.current_table.scope,
            line_pos=line_num,
            is_mutable=False,
            kind="function",
            params =None,
            return_type = None,
            parent_class= parent_class_name,
            dim=0

        ):
            self.add_error(ctx, f"Clase {class_name} redeclarada")

        self.enter_scope(f"class_{class_name}")

        old_class = self.current_class
        self.current_class = class_name
        self.constructor_params = []
        self.has_constructor = False
        for m in ctx.classMember():
            self.visit(m) 

        if self.has_constructor:
            self.current_table[class_name].has_constructor = True
            self.current_table[class_name].constructor_params = self.constructor_params
        
        self.current_class = old_class
        self.exit_scope()


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


    def visitPrimaryExpr(self, ctx):
        if hasattr(ctx, "literalExpr") and ctx.literalExpr():
            b, d = self.visit(ctx.literalExpr())
            return self._set_inferred(ctx, b, d)

        if hasattr(ctx, "Identifier") and ctx.Identifier():
            name = ctx.Identifier().getText()
            sym = self.current_table.lookup_global(name)
            if sym:
                return self._set_inferred(ctx, getattr(sym,'type',None), getattr(sym,'dim',0))
            self.add_error(ctx, f"Identificador no declarado: {name}")
            return self._set_inferred(ctx, None, 0)

        self.visitChildren(ctx)
        return self._get_inferred(ctx)

    # Visit a parse tree produced by CompiscriptParser#literalExpr.
    def visitLiteralExpr(self, ctx):
        # Si es array literal, delega
        if hasattr(ctx, "arrayLiteral") and ctx.arrayLiteral():
            b, d = self.visit(ctx.arrayLiteral())
            return self._set_inferred(ctx, b, d)

        txt = ctx.getText()
        if re.fullmatch(r"\d+", txt):          return self._set_inferred(ctx, "integer", 0)
        if txt in ("true","false"):            return self._set_inferred(ctx, "boolean", 0)
        if len(txt) >= 2 and txt[0]=='"' and txt[-1]=='"':
                                            return self._set_inferred(ctx, "string", 0)
        if txt == "null":                      return self._set_inferred(ctx, "null", 0)
        return self._set_inferred(ctx, None, 0)


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
    def visitArrayLiteral(self, ctx):
        elems = list(ctx.expression()) if ctx.expression() else []
        if not elems:
            return self._set_inferred(ctx, None, 1)

        bases, dims = [], []
        for e in elems:
            b, d = self.infer_type_and_dim(e)
            bases.append(b); dims.append(d)

        known = [b for b in bases if b is not None]
        if known and any(b != known[0] for b in known):
            self.add_error(ctx, f"Literal de arreglo heterogéneo: {set(known)}")
            base = None
        else:
            base = known[0] if known else None

        # Rectangularidad (si no permites jagged)
        if any(d != dims[0] for d in dims):
            self.add_error(ctx, "Arreglo no rectangular")

        return self._set_inferred(ctx, base, 1 + (dims[0] if dims else 0))

    # Visit a parse tree produced by CompiscriptParser#type.
    def visitType(self, ctx:CompiscriptParser.TypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#baseType.
    def visitBaseType(self, ctx:CompiscriptParser.BaseTypeContext):
        return self.visitChildren(ctx)



del CompiscriptParser
