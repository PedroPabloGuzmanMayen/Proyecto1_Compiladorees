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

    def _visit_and_get(self, node):
        res = self.visit(node)
        if isinstance(res, tuple) and len(res) == 2:
            return res
        return self._get_inferred(node)

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
        if not ctx:
            return None, 0
        return self._visit_and_get(ctx)


    def infer_type_and_dim(self, expr_ctx):
        if not expr_ctx:
            return None, 0

  
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
        if re.fullmatch(r"\d+", text):
            return "integer", 0
        if text in ("true", "false"):
            return "boolean", 0
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            return "string", 0
        if text == "null":
            return "null", 0

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
    

    def _lookup_class(self, name):
        sym = self.current_table.lookup_global(name)
        return sym if sym and getattr(sym, "kind", None) == "class" else None

    def _lookup_member(self, class_name, prop):
        cls = self._lookup_class(class_name)
        while cls:
            if hasattr(cls, "members") and prop in cls.members:
                return cls.members[prop]
            parent = getattr(cls, "parent_class", None)
            cls = self._lookup_class(parent) if parent else None
        return None


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
        var_name = ctx.Identifier().getText()
        line_num = self.get_line_number(ctx)

        if ctx.typeAnnotation():
            var_type, dimensions = self.parse_type(ctx.typeAnnotation().type_())
        else:
            var_type, dimensions = None, 0
            self.add_error(ctx, f"La variable '{var_name}' debe tener tipo explícito")

        if ctx.initializer():
            inferred_type, inferred_dim = self.infer_type_and_dim(ctx.initializer().expression())
            if inferred_type is None and inferred_dim > 0 and var_type:
                inferred_type = var_type
            if var_type and inferred_type and var_type != inferred_type:
                self.add_error(ctx, f"Tipo incompatible: {var_type} vs {inferred_type}")
            if dimensions and inferred_dim and dimensions != inferred_dim:
                self.add_error(ctx, f"Dimensión incompatible: {dimensions} vs {inferred_dim}")

        if not self.current_table.insert_symbol(
            identifier=var_name, type=var_type, scope=self.current_table.scope, line_pos=line_num,
            is_mutable=True, kind="variable", params=[], return_type=None, parent_class=None, dim=dimensions
        ):
            self.add_error(ctx, f"Variable {var_name} ya declarada!")



        if self.current_class and self.current_function is None:
            cls_sym = self.current_table.lookup_global(self.current_class)
            if cls_sym and getattr(cls_sym, "kind", None) == "class":
                if not hasattr(cls_sym, "members"):
                    cls_sym.members = {}

                if var_name in cls_sym.members:
                    self.add_error(ctx, f"Miembro '{var_name}' ya existe en la clase {self.current_class}")
                else:
                    field_reg = Register(
                        identifier=var_name,
                        type=var_type,
                        scope=self.current_table.scope,
                        line_pos=line_num,
                        is_mutable=True,
                        kind="field",
                        params=[],
                        return_type=None,
                        parent_class=self.current_class,
                        dim=dimensions
                    )
                    cls_sym.members[var_name] = field_reg


    # Visit a parse tree produced by CompiscriptParser#constantDeclaration.
    def visitConstantDeclaration(self, ctx):
        """Define la declaración de una constante"""
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

            if expr_base is None and expr_dim > 0 and decl_base:
                expr_base = decl_base

        if decl_base and expr_base and decl_base != expr_base:
            self.add_error(ctx, f"Tipo incompatible: {decl_base} vs {expr_base}")
        if decl_dim and expr_dim and decl_dim != expr_dim:
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
        cond_type, _ = self.infer_expression_type(cond_ctx)
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

            if ctx.block(0):
                self.enter_scope(f"try_{self.get_line_number(ctx)}")
                self.visit(ctx.block(0))
                self.exit_scope()

            catch_id = None

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
            switch_type,_ = self.infer_expression_type(switch_expr)
            if switch_type is None:
                self.add_error(ctx, "No se pudo inferir tipo de la expresión del switch")

            seen_cases = set()
            # ctx.switchCase() # devuelve lista de case contexts
            for case_ctx in list(ctx.switchCase()):
                case_expr = case_ctx.expression()
                case_type,_ = self.infer_expression_type(case_expr)
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
                for st in ctx.defaultCase().statement():
                    self.visit(st)
        except Exception as e:
            self.add_error(ctx, str(e))
        return None

    def visitAssignment(self, ctx:CompiscriptParser.AssignmentContext):
        try:
            if ctx.getChildCount() >= 2 and ctx.getChild(1).getText() == '.':
                left_expr  = ctx.expression(0)
                prop_name  = ctx.Identifier().getText()
                right_expr = ctx.expression(1)

                owner_type, owner_dim = self.infer_type_and_dim(left_expr)
                if owner_type is None:
                    if left_expr.getText() == "this" and self.current_class:
                        owner_type, owner_dim = self.current_class, 0
                    else:
                        self.add_error(ctx, "No se pudo inferir el tipo del objeto al asignar propiedad")
                        self.visit(right_expr)
                        return None
                if owner_dim != 0:
                    self.add_error(ctx, f"No se pueden asignar propiedades en arrays (tipo {owner_type}[{owner_dim}])")
                    self.visit(right_expr)
                    return None
                
                mem = self._lookup_member(owner_type, prop_name)
                if not mem:
                    self.add_error(ctx, f"Clase '{owner_type}' no tiene propiedad '{prop_name}'")
                    self.visit(right_expr)
                    return None
                
                if getattr(mem, "kind", "") in ("method", "function", "constructor"):
                    self.add_error(ctx, f"No se puede asignar al método '{owner_type}.{prop_name}'")
                    self.visit(right_expr)
                    return None
                
                rhs_t, rhs_d = self.infer_type_and_dim(right_expr)
                if mem.type and rhs_t and mem.type != rhs_t:
                    self.add_error(ctx, f"Tipo incompatible al asignar '{owner_type}.{prop_name}': "
                                        f"esperado {mem.type}, recibido {rhs_t}")
                if (mem.dim or 0) != (rhs_d or 0):
                    self.add_error(ctx, f"Dimensión incompatible al asignar '{owner_type}.{prop_name}': "
                                        f"esperada {mem.dim or 0}, recibida {rhs_d or 0}")

 
                self.visit(left_expr)
                self.visit(right_expr)
                return None

        except Exception as e:
            self.add_error(ctx, str(e))
            return None


    def visitAssignExpr(self, ctx):
     
        lhs_type, lhs_dim = self.infer_type_and_dim(ctx.lhs)

        rhs_node = None
   
        if hasattr(ctx, "assignmentExpr") and callable(ctx.assignmentExpr):
            rhs_node = ctx.assignmentExpr()
  
        if rhs_node is None and hasattr(ctx, "expression") and callable(ctx.expression):
            rhs_node = ctx.expression()

        if rhs_node is None:
            if ctx.getChildCount() >= 3 and ctx.getChild(1).getText() == '=':
                rhs_node = ctx.getChild(2)

        rhs_type, rhs_dim = self._visit_and_get(rhs_node) if rhs_node is not None else (None, 0)

        if ctx.lhs.primaryAtom() and ctx.lhs.primaryAtom().Identifier():
            name = ctx.lhs.primaryAtom().Identifier().getText()
            sym = self.current_table.lookup_global(name)
            if sym and not sym.is_mutable:
                self.add_error(ctx, f"No se puede asignar a constante '{name}'")
            if sym and (sym.type != rhs_type or sym.dim != rhs_dim):
                self.add_error(ctx, f"Tipo incompatible en asignación a '{name}': "
                                    f"{sym.type}[{sym.dim}] vs {rhs_type}[{rhs_dim}]")

        return self._set_inferred(ctx, rhs_type, rhs_dim)


    def visitPropertyAssignExpr(self, ctx):
        obj_type, obj_dim = self.infer_type_and_dim(ctx.lhs)
        rhs_type, rhs_dim = self.infer_type_and_dim(ctx.assignmentExpr())

        prop = ctx.Identifier().getText()

        return self._set_inferred(ctx, rhs_type, rhs_dim)

    def visitWhileStatement(self, ctx:CompiscriptParser.WhileStatementContext):
        """Verifica la condición del while y marca que estamos dentro de un bucle."""
        self.enter_scope(f"while_{self.get_line_number(ctx)}")
        cond_ctx = ctx.expression()
        cond_type, _ = self.infer_expression_type(cond_ctx)
        if cond_type is None:
            self.add_error(ctx, f"No se pudo inferir tipo de la condición del while")
        elif cond_type != "boolean":
            self.add_error(ctx, f"Condición de while debe ser boolean (obtenido: {cond_type})")

        self.in_loop += 1
        # visitar el bloque del while 
        if ctx.block():
            self.visit(ctx.block())
        self.in_loop -= 1
        self.exit_scope()
        return None

    def visitDoWhileStatement(self, ctx:CompiscriptParser.DoWhileStatementContext):
        """Visita el bloque do y luego verifica la condición del while."""
        self.enter_scope(f"while_{self.get_line_number(ctx)}")
        self.in_loop += 1
        if ctx.block():
            self.visit(ctx.block())

        cond_ctx = ctx.expression()
        cond_type,_ = self.infer_expression_type(cond_ctx)
        if cond_type is None:
            self.add_error(ctx, f"No se pudo inferir tipo de la condición del do-while")
        elif cond_type != "boolean":
            self.add_error(ctx, f"Condición de do-while debe ser boolean (obtenido: {cond_type})")

        self.in_loop -= 1
        self.exit_scope()
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
            cond_type,_ = self.infer_expression_type(cond)
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


    # Visit a parse tree produced by CompiscriptParser#expressionStatement.
    def visitExpressionStatement(self, ctx:CompiscriptParser.ExpressionStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#printStatement.
    def visitPrintStatement(self, ctx:CompiscriptParser.PrintStatementContext):
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
            return_type, return_dim = self._visit_and_get(ctx.expression())
        else:
            return_type, return_dim = None, 0

        # Caso función void
        if self.expected_return_type is None and ctx.expression():
            self.add_error(ctx, "La función es void pero hay un valor en return")

        # Caso función con tipo esperado
        if self.expected_return_type is not None:
            if return_type != self.expected_return_type:
                self.add_error(
                    ctx,
                    f"Tipo de retorno esperado {self.expected_return_type} y recibido {return_type}"
                )
            if return_dim != (self.expected_dim or 0):
                self.add_error(
                    ctx,
                    f"Dimensión de retorno esperada {self.expected_dim} y recibida {return_dim}"
                )

        self.found_return = True
        return self._set_inferred(ctx, return_type, return_dim)




    # Visit a parse tree produced by CompiscriptParser#switchCase.
    def visitSwitchCase(self, ctx:CompiscriptParser.SwitchCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#defaultCase.
    def visitDefaultCase(self, ctx:CompiscriptParser.DefaultCaseContext):
        return self.visitChildren(ctx)
    
    def visitForeachStatement(self, ctx:CompiscriptParser.ForeachStatementContext):
        """
        Maneja foreach (let item in arr) { ... }
        """
        iter_var = ctx.Identifier().getText()
        expr_ctx = ctx.expression()

  
        base_type, base_dim = self.infer_type_and_dim(expr_ctx)
        if base_type is None and expr_ctx.getText().isidentifier():
            sym = self.current_table.lookup_global(expr_ctx.getText())
            if sym:
                base_type, base_dim = sym.type, sym.dim


        if base_dim <= 0:
            self.add_error(ctx, f"La expresión en foreach debe ser un arreglo (obtenido: {base_type}[{base_dim}])")
            item_type, item_dim = None, 0
        else:
            item_type, item_dim = base_type, base_dim - 1

        self.in_loop +=1
        self.enter_scope(f"foreach_{self.get_line_number(ctx)}")

        inserted = self.current_table.insert_symbol(
            identifier=iter_var,
            type=base_type,
            scope=self.current_table.scope,
            line_pos=self.get_line_number(ctx),
            is_mutable=True,
            kind="variable",
            params=[],
            return_type=None,
            parent_class=None,
            dim=base_dim - 1 if base_dim > 0 else 0
        )
        if not inserted:
            self.add_error(ctx, f"Variable '{iter_var}' ya declarada en este ámbito")


        if ctx.block():
            self.visit(ctx.block())

        # Salir del scope
        self.exit_scope()
        self.in_loop -=1
        return None



    # Visit a parse tree produced by CompiscriptParser#functionDeclaration.
    def visitFunctionDeclaration(self, ctx):
        """Verifica declaraciones de funciones"""

        func_name = ctx.Identifier().getText()
        line_num = self.get_line_number(ctx)
        function_return_type = None
        function_return_dim = 0
        
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

        in_class = self.current_class is not None
        is_ctor  = in_class and (func_name == "constructor")


        if is_ctor:
            if ctx.type_():
                self.add_error(ctx, "El constructor no debe declarar tipo de retorno")
            function_return_type, function_return_dim = None, 0
            cls = self.current_table.lookup_global(self.current_class)
            if cls:
                cls.has_constructor = True
                cls.constructor_params = params
        kind = "constructor" if is_ctor else ("method" if in_class else "function")


        # Declarar la función en el ámbito actual
        if not self.current_table.insert_symbol(
            identifier=func_name,
            type=function_return_type,
            scope = self.current_table.scope,
            line_pos=line_num,
            is_mutable=False,
            kind="function",
            params =params,
            return_type=function_return_type,
            parent_class= None,
            dim=0
        ):
            self.add_error(ctx, f"Redeclaración de la función {func_name}")

        if in_class:
            cls_sym = self.current_table.lookup_global(self.current_class)
            if cls_sym and getattr(cls_sym, "kind", None) == "class":
                if not hasattr(cls_sym, "members"):
                    cls_sym.members = {}
                if func_name in cls_sym.members:
                    self.add_error(ctx, f"Miembro '{func_name}' ya existe en la clase {self.current_class}")
                else:
                    cls_sym.members[func_name] = Register(
                        identifier=func_name,
                        type=function_return_type,
                        scope=self.current_table.scope,
                        line_pos=line_num,
                        is_mutable=False,
                        kind=kind,
                        params=params,
                        return_type=function_return_type,
                        parent_class=self.current_class,
                        dim=function_return_dim
                    )
        
        # Entrar al ámbito de la función
        self.enter_scope(f"function_{func_name}")
        old_function = self.current_function
        self.current_function = func_name
        self.found_return = False
        self.expected_return_type = function_return_type
        self.expected_dim = function_return_dim

        if in_class:
            self.current_table.insert_symbol(
                identifier="this",
                type=self.current_class,
                scope=self.current_table.scope,
                line_pos=line_num,
                is_mutable=True,
                kind="variable",
                params=[],
                return_type=None,
                parent_class=self.current_class,
                dim=0
            )
        
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
        ids = ctx.Identifier()
        class_name = ids[0].getText()
        parent_class_name  = ids[1].getText() if len(ids) > 1 else None
        line_num = self.get_line_number(ctx)

       
        if not self.current_table.insert_symbol(
            identifier=class_name, type=None, scope=self.current_table.scope, line_pos=line_num,
            is_mutable=False, kind="class", params=None, return_type=None, parent_class=parent_class_name, dim=0
        ):
            self.add_error(ctx, f"Clase {class_name} redeclarada")

     
        cls_sym = self.current_table.lookup_global(class_name)
        if not cls_sym:
            self.add_error(ctx, f"No se pudo registrar la clase {class_name}")
            return None

        if not hasattr(cls_sym, "members"):
            cls_sym.members = {}

        # Entrar al scope de la clase
        self.enter_scope(f"class_{class_name}")

        old_class = self.current_class
        self.current_class = class_name
        self.constructor_params = []
        self.has_constructor = False

        for m in ctx.classMember():
            self.visit(m)

        if self.has_constructor:
            cls_sym.has_constructor = True
            cls_sym.constructor_params = self.constructor_params

        self.current_class = old_class
        self.exit_scope()



    # Visit a parse tree produced by CompiscriptParser#classMember.
    def visitClassMember(self, ctx:CompiscriptParser.ClassMemberContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by CompiscriptParser#expression.
    def visitExpression(self, ctx:CompiscriptParser.ExpressionContext):
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
    def visitLogicalOrExpr(self, ctx):
        lb, ld = self._visit_and_get(ctx.logicalAndExpr(0))
        for i in range(1, len(ctx.logicalAndExpr())):
            rb, rd = self._visit_and_get(ctx.logicalAndExpr(i))
            if not (lb == "boolean" and ld == 0 and rb == "boolean" and rd == 0):
                self.add_error(ctx, f"Operador '||' requiere boolean || boolean (obtenido: {lb}[{ld}] y {rb}[{rd}])")
            lb, ld = "boolean", 0
        return self._set_inferred(ctx, lb, ld)


    # Visit a parse tree produced by CompiscriptParser#logicalAndExpr.
    def visitLogicalAndExpr(self, ctx):
        lb, ld = self._visit_and_get(ctx.equalityExpr(0))
        for i in range(1, len(ctx.equalityExpr())):
            rb, rd = self._visit_and_get(ctx.equalityExpr(i))
            if not (lb == "boolean" and ld == 0 and rb == "boolean" and rd == 0):
                self.add_error(ctx, f"Operador '&&' requiere boolean && boolean (obtenido: {lb}[{ld}] y {rb}[{rd}])")
            lb, ld = "boolean", 0
        return self._set_inferred(ctx, lb, ld)


    # Visit a parse tree produced by CompiscriptParser#equalityExpr.
    def visitEqualityExpr(self, ctx):
        lb, ld = self._visit_and_get(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            rb, rd = self._visit_and_get(ctx.relationalExpr(i))
            if lb is None or rb is None or ld != rd or lb != rb:
                self.add_error(ctx, f"No se pueden comparar {lb}[{ld}] con {rb}[{rd}]")
            lb, ld = "boolean", 0
        return self._set_inferred(ctx, lb, ld)


    # Visit a parse tree produced by CompiscriptParser#relationalExpr.
    def visitRelationalExpr(self, ctx):
        lb, ld = self._visit_and_get(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            rb, rd = self._visit_and_get(ctx.additiveExpr(i))
            if not (lb == "integer" and ld == 0 and rb == "integer" and rd == 0):
                self.add_error(ctx, f"Comparaciones relacionales requieren enteros escalares (obtenido: {lb}[{ld}] y {rb}[{rd}])")
            lb, ld = "boolean", 0
        return self._set_inferred(ctx, lb, ld)


    # Visit a parse tree produced by CompiscriptParser#additiveExpr.
    def visitAdditiveExpr(self, ctx):
        lb, ld = self._visit_and_get(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            rb, rd = self._visit_and_get(ctx.multiplicativeExpr(i))
            op = ctx.getChild(2*i-1).getText()

            if op == '+':
                if (lb, ld) == ("integer", 0) and (rb, rd) == ("integer", 0):
                    lb, ld = "integer", 0
                elif (lb == "string" and ld == 0) or (rb == "string" and rd == 0) \
                    or (lb == "exception" and ld == 0 and rb == "string" and rd == 0) \
                    or (rb == "exception" and rd == 0 and lb == "string" and ld == 0):
                    lb, ld = "string", 0
                else:
                    self.add_error(ctx, f"Operación '+' inválida entre {lb}[{ld}] y {rb}[{rd}]")
                    lb, ld = None, 0

            elif op == '-':
                if (lb, ld) == ("integer", 0) and (rb, rd) == ("integer", 0):
                    lb, ld = "integer", 0
                else:
                    self.add_error(ctx, f"Operación '-' inválida entre {lb}[{ld}] y {rb}[{rd}]")
                    lb, ld = None, 0
            else:
                self.add_error(ctx, f"Operación '{op}' inválida entre {lb}[{ld}] y {rb}[{rd}]")
                lb, ld = None, 0

        return self._set_inferred(ctx, lb, ld)



    # Visit a parse tree produced by CompiscriptParser#multiplicativeExpr.
    def visitMultiplicativeExpr(self, ctx):
        lb, ld = self._visit_and_get(ctx.unaryExpr(0))
        for i in range(1, len(ctx.unaryExpr())):
            rb, rd = self._visit_and_get(ctx.unaryExpr(i))
            op = ctx.getChild(2*i-1).getText()

            if (lb, ld) == ("integer", 0) and (rb, rd) == ("integer", 0):
                lb, ld = "integer", 0
            else:
                self.add_error(ctx, f"Operación '{op}' inválida entre {lb}[{ld}] y {rb}[{rd}]")
                lb, ld = None, 0
        return self._set_inferred(ctx, lb, ld)

    # Visit a parse tree produced by CompiscriptParser#unaryExpr.
    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() == 2:
            op = ctx.getChild(0).getText()
            rb, rd = self._visit_and_get(ctx.getChild(1))
            if op == '!':
                if not (rb == "boolean" and rd == 0):
                    self.add_error(ctx, f"Operador '!' requiere boolean (obtenido: {rb}[{rd}])")
                return self._set_inferred(ctx, "boolean", 0)
            elif op in ('+', '-'):
                if not (rb == "integer" and rd == 0):
                    self.add_error(ctx, f"Operador '{op}' unario requiere integer (obtenido: {rb}[{rd}])")
                return self._set_inferred(ctx, "integer", 0)

        return self._visit_and_get(ctx.getChild(0))

    def visitPrimaryExpr(self, ctx):
        # Caso: literal
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())

        # Caso: identificador o this/new
        if ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())

        # Caso: expresión entre paréntesis
        if ctx.expression():
            return self.visit(ctx.expression())

        return self._set_inferred(ctx, None, 0)


    # Visit a parse tree produced by CompiscriptParser#literalExpr.
    def visitArrayLiteral(self, ctx):
        elems = ctx.expression()
        if not elems:
            return self._set_inferred(ctx, None, 1)

        bases, dims = [], []
        for e in elems:
            b, d = self.infer_type_and_dim(e)
            bases.append(b); dims.append(d)

        known = [b for b in bases if b is not None]
        if known and any(b != known[0] for b in known):
            self.add_error(ctx, f"Arreglo heterogéneo: {set(known)}")
            return self._set_inferred(ctx, None, 0)

        if any(d != dims[0] for d in dims):
            self.add_error(ctx, "Arreglo no rectangular")
            return self._set_inferred(ctx, None, 0)

        base = known[0] if known else None
        return self._set_inferred(ctx, base, 1 + (dims[0] if dims else 0))


    # Visit a parse tree produced by CompiscriptParser#leftHandSide.
    def visitLeftHandSide(self, ctx):
        base_type, base_dim = self.visit(ctx.primaryAtom())

        last_member = None 

        for suf in ctx.suffixOp():
            head = suf.getChild(0).getText()

            if head == '.':
                prop = suf.Identifier().getText()
                if base_dim != 0:
                    self.add_error(ctx, f"No se pueden acceder propiedades en arrays (tipo {base_type}[{base_dim}])")
                    base_type, base_dim, last_member = (None, 0), 0, None
                    continue

                cls = self._lookup_class(base_type)
                if not cls:
                    self.add_error(ctx, f"Tipo '{base_type}' no es una clase con propiedades")
                    base_type, base_dim, last_member = (None, 0), 0, None
                    continue

                mem = self._lookup_member(base_type, prop)
                if not mem:
                    self.add_error(ctx, f"Clase '{base_type}' no tiene propiedad/método '{prop}'")
                    base_type, base_dim, last_member = (None, 0), 0, None
                    continue

                base_type, base_dim = (mem.type or mem.return_type, mem.dim)
                last_member = mem  

            elif head == '(':
                if last_member is not None:
                    args = suf.arguments().expression() if suf.arguments() else []
                    if len(args) != len(last_member.params):
                        self.add_error(ctx, f"Método '{last_member.identifier}' esperaba {len(last_member.params)} parámetros, se dieron {len(args)}")
                    else:
                        for a, p in zip(args, last_member.params):
                            t, d = self.infer_type_and_dim(a)
                            if p["type"] and t != p["type"]:
                                self.add_error(ctx, f"Parámetro '{p['name']}' esperaba {p['type']}, recibido {t}")
                            if d != (p.get("dimension") or 0):
                                self.add_error(ctx, f"Dimensión del parámetro '{p['name']}' esperaba {p.get('dimension') or 0}, recibió {d}")

                    base_type, base_dim = (last_member.return_type or last_member.type, last_member.dim or 0)
                    last_member = None
                else:
        
                    rb, rd = self.visit(suf)  
                    base_type, base_dim = rb, rd

            elif head == '[':
                idx_type, idx_dim = self.infer_type_and_dim(suf.expression())
                if idx_type != "integer" or idx_dim != 0:
                    self.add_error(ctx, f"Índice debe ser integer, no {idx_type}[{idx_dim}]")
                base_dim -= 1
                if base_dim < 0:
                    self.add_error(ctx, "Acceso inválido a arreglo (dimensión negativa)")

            else:
                self.visit(suf)

        return self._set_inferred(ctx, base_type, base_dim)


    # Visit a parse tree produced by CompiscriptParser#IdentifierExpr.
    def visitIdentifierExpr(self, ctx):
        name = ctx.Identifier().getText()
        sym = self.current_table.lookup_global(name)
        if sym:
            return self._set_inferred(ctx, sym.type, sym.dim)
        self.add_error(ctx, f"Identificador no declarado: {name}")
        return self._set_inferred(ctx, None, 0)
    
    def visitLiteralExpr(self, ctx):
        txt = ctx.getText()

        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())

        if txt.isdigit():
            return self._set_inferred(ctx, "integer", 0)
        if txt in ("true", "false"):
            return self._set_inferred(ctx, "boolean", 0)
        if txt.startswith('"') and txt.endswith('"'):
            return self._set_inferred(ctx, "string", 0)
        if txt == "null":
            return self._set_inferred(ctx, "null", 0)

        return self._set_inferred(ctx, None, 0)

    # Visit a parse tree produced by CompiscriptParser#NewExpr.
    def visitNewExpr(self, ctx):
        class_name = ctx.Identifier().getText()
        sym = self.current_table.lookup_global(class_name)
        if not sym or sym.kind != "class":
            self.add_error(ctx, f"Clase '{class_name}' no declarada")
            return self._set_inferred(ctx, None, 0)
        # Por ahora, retornamos el nombre de la clase como tipo
        return self._set_inferred(ctx, class_name, 0)


    # Visit a parse tree produced by CompiscriptParser#ThisExpr.
    def visitThisExpr(self, ctx):
        if not self.current_class:
            self.add_error(ctx, "'this' usado fuera de una clase")
            return self._set_inferred(ctx, None, 0)
        return self._set_inferred(ctx, self.current_class, 0)


    # Visit a parse tree produced by CompiscriptParser#CallExpr.
    def visitCallExpr(self, ctx):

        parent = ctx.parentCtx
        func_name = None

        if hasattr(parent, "Identifier") and parent.Identifier():
            # caso f(x,y)
            func_name = parent.Identifier().getText()

        if func_name:
            sym = self.current_table.lookup_global(func_name)
            if not sym or sym.kind != "function":
                self.add_error(ctx, f"Llamada a '{func_name}' que no es función")
                return self._set_inferred(ctx, None, 0)

            args = ctx.arguments().expression() if ctx.arguments() else []
            if len(args) != len(sym.params):
                self.add_error(ctx, f"Función '{func_name}' esperaba {len(sym.params)} parámetros, se dieron {len(args)}")

            for a, param in zip(args, sym.params):
                t, d = self.infer_type_and_dim(a)
                if param["type"] and t != param["type"]:
                    self.add_error(ctx, f"Parámetro '{param['name']}' esperaba {param['type']}, recibido {t}")


            return self._set_inferred(ctx, sym.type, sym.dim or 0)

        return self._set_inferred(ctx, None, 0)


    # Visit a parse tree produced by CompiscriptParser#IndexExpr.
    def visitIndexExpr(self, ctx):
        """
        Maneja indexación de arrays: a[0]
        """
        # tipo del objeto a indexar
        base_type, base_dim = self.infer_type_and_dim(ctx.parentCtx.parentCtx.primaryAtom())

        # tipo del índice
        idx_type, idx_dim = self.infer_type_and_dim(ctx.expression())
        if idx_type != "integer" or idx_dim != 0:
            self.add_error(ctx, f"Índice de array debe ser integer, no {idx_type}[{idx_dim}]")

        if base_dim <= 0:
            self.add_error(ctx, f"Acceso inválido, no es arreglo")
            return self._set_inferred(ctx, None, 0)

        return self._set_inferred(ctx, base_type, base_dim - 1)

    # Visit a parse tree produced by CompiscriptParser#PropertyAccessExpr.
    def visitPropertyAccessExpr(self, ctx):
        """
        Maneja acceso a propiedades de clases/objetos: obj.prop
        """
        # tipo del objeto
        obj_type, obj_dim = self.infer_type_and_dim(ctx.parentCtx.parentCtx.primaryAtom())
        prop = ctx.Identifier().getText()

        if obj_dim != 0:
            self.add_error(ctx, f"No se pueden acceder propiedades en arrays (tipo {obj_type}[{obj_dim}])")
            return self._set_inferred(ctx, None, 0)

        # buscar la clase en la tabla de símbolos
        sym = self.current_table.lookup_global(obj_type)
        if not sym or sym.kind != "class":
            self.add_error(ctx, f"Tipo '{obj_type}' no es una clase con propiedades")
            return self._set_inferred(ctx, None, 0)

        # si tienes guardado en la clase un diccionario con atributos:
        if hasattr(sym, "members") and prop in sym.members:
            return self._set_inferred(ctx, sym.members[prop].type, sym.members[prop].dim)

        self.add_error(ctx, f"Clase '{obj_type}' no tiene propiedad '{prop}'")
        return self._set_inferred(ctx, None, 0)

    # Visit a parse tree produced by CompiscriptParser#arguments.
    def visitArguments(self, ctx:CompiscriptParser.ArgumentsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#arrayLiteral.
    def visitArrayLiteral(self, ctx):

        elems = ctx.expression()
        if not elems:
            return self._set_inferred(ctx, None, 1)

        bases, dims = [], []
        for e in elems:
            b, d = self.infer_type_and_dim(e)
            bases.append(b); dims.append(d)

        known = [b for b in bases if b is not None]
        if known and any(b != known[0] for b in known):
            self.add_error(ctx, f"Arreglo heterogéneo: {set(known)}")

        if any(d != dims[0] for d in dims):
            self.add_error(ctx, "Arreglo no rectangular")

        base = known[0] if known else None
        return self._set_inferred(ctx, base, 1 + (dims[0] if dims else 0))

    # Visit a parse tree produced by CompiscriptParser#type.
    def visitType(self, ctx:CompiscriptParser.TypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#baseType.
    def visitBaseType(self, ctx:CompiscriptParser.BaseTypeContext):
        return self.visitChildren(ctx)



del CompiscriptParser
