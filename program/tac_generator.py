from antlr4 import *
from instruction_table import Quadruple
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from CompiscriptVisitor import CompiscriptVisitor
from symbolTable import Register, Symbol_table
import re

class tac_generator(CompiscriptVisitor):

    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.quadruple_table = Quadruple()
        self.offset = 0
        self.temporal_counter = 0
        self.available_temporals = []
        self.in_use_temporals = []
        self.old_table = []

    def temporal_generator(self):
        self.temporal_counter += 1
        return f"t{self.temporal_counter}"
    
    def memory_allocator(self, type, dimension, size):
        pass

    def get_line_number(self, ctx):
        return ctx.start.line if ctx.start else 0

        
    def free_temporal(self, id):
        pass
    def reset_temporal_counter(self):
        self.temporal_counter = 0

    # Visit a parse tree produced by CompiscriptParser#program.
    def visitProgram(self, ctx:CompiscriptParser.ProgramContext):
        for statement in ctx.statement():
            self.visit(statement)
        return None


    # Visit a parse tree produced by CompiscriptParser#statement.
    def visitStatement(self, ctx:CompiscriptParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#block.
    def visitBlock(self, ctx:CompiscriptParser.BlockContext):
        """Visita un bloque de código"""
        for statement in ctx.statement():
            self.visit(statement)
        return None


    # Visit a parse tree produced by CompiscriptParser#variableDeclaration.
    def visitVariableDeclaration(self, ctx:CompiscriptParser.VariableDeclarationContext):

        var_name = ctx.Identifier().getText()
        var_type = self.symbol_table.elements[var_name].type
        var_dimension = self.symbol_table.elements[var_name].dim
        if ctx.initializer():
            value = self.visit(ctx.initializer())
            self.quadruple_table.insert_into_table("=", value, None, var_name)
        self.reset_temporal_counter()

        return var_name
    


    # Visit a parse tree produced by CompiscriptParser#constantDeclaration.
    def visitConstantDeclaration(self, ctx:CompiscriptParser.ConstantDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#typeAnnotation.
    def visitTypeAnnotation(self, ctx:CompiscriptParser.TypeAnnotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#initializer.
    def visitInitializer(self, ctx:CompiscriptParser.InitializerContext):
        return self.visit(ctx.expression())


    # Visit a parse tree produced by CompiscriptParser#assignment.
    def visitAssignment(self, ctx:CompiscriptParser.AssignmentContext):
        # Caso simple: Identifier '=' expression ';'
        if ctx.Identifier() and len(ctx.expression()) == 1:
            name = ctx.Identifier().getText()
            value = self.visit(ctx.expression(0))
            self.quadruple_table.insert_into_table("=", value, None, name)
            return name

        # Caso: expression '.' Identifier '=' expression ';'
        elif len(ctx.expression()) == 2:
            obj = self.visit(ctx.expression(0))
            prop = ctx.Identifier().getText()
            value = self.visit(ctx.expression(1))
            target = f"{obj}.{prop}"
            self.quadruple_table.insert_into_table("=", value, None, target)
            return target

        # fallback
        return None


    # Visit a parse tree produced by CompiscriptParser#expressionStatement.
    def visitExpressionStatement(self, ctx:CompiscriptParser.ExpressionStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#printStatement.
    def visitPrintStatement(self, ctx:CompiscriptParser.PrintStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#ifStatement.
    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        # Generar etiquetas únicas
        line = int(self.get_line_number(ctx))
        Ltrue = f"L{line}"
        Lfalse = f"L{line + 1}"
        Lend = f"L{line + 2}"

        condition = self.visit(ctx.expression())

        self.quadruple_table.insert_into_table("if", condition, "goto", Ltrue)
        self.quadruple_table.insert_into_table("goto", Lfalse, None, None)

        self.quadruple_table.insert_into_table("label", None, None, Ltrue)
        old_table = self.symbol_table
        self.symbol_table = old_table.scope_map.get(f"if_{line}", old_table)
        self.visit(ctx.block(0))
        self.symbol_table = old_table

        if len(ctx.block()) > 1:
            self.quadruple_table.insert_into_table("goto", Lend, None, None)

        self.quadruple_table.insert_into_table("label", None, None, Lfalse)
        if len(ctx.block()) > 1:
            self.symbol_table = old_table.scope_map.get(f"else_{line}", old_table)
            self.visit(ctx.block(1))
            self.symbol_table = old_table

        # --- Fin del if ---
        if len(ctx.block()) > 1:
            self.quadruple_table.insert_into_table("label", None, None, Lend)

        return None

        


    # Visit a parse tree produced by CompiscriptParser#whileStatement.
    def visitWhileStatement(self, ctx:CompiscriptParser.WhileStatementContext):
        initial_tag = "L" + str(self.get_line_number(ctx))
        next_tag = "L" + str(1+int(self.get_line_number(ctx)))
        final_tag = "L" + str(2+int(self.get_line_number(ctx)))
        self.quadruple_table.insert_into_table("label", None, None, initial_tag + ":")
        value = self.visit(ctx.expression())
        self.quadruple_table.insert_into_table("if", value, "goto", next_tag)
        self.quadruple_table.insert_into_table("goto", final_tag, None, None)
        if ctx.block():
            self.quadruple_table.insert_into_table("label", None, None, next_tag + ":")
            old_table = self.symbol_table
            self.symbol_table = old_table.scope_map["while_" + str(self.get_line_number(ctx))]
            self.visit(ctx.block())
            self.quadruple_table.insert_into_table("goto", initial_tag, None, None)
            self.quadruple_table.insert_into_table("label", None, None, final_tag + ":")
            self.symbol_table = old_table


    # Visit a parse tree produced by CompiscriptParser#doWhileStatement.
    def visitDoWhileStatement(self, ctx:CompiscriptParser.DoWhileStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#forStatement.
    def visitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        ln = self.get_line_number(ctx)
        start_lbl = f"L{ln}_start"
        body_lbl = f"L{ln}_body"
        update_lbl = f"L{ln}_update"
        after_lbl = f"L{ln}_after"
        old_table = self.symbol_table
        scope_key = f"for_{ln}"
        self.symbol_table = old_table.scope_map[scope_key]

        init_done = False
        if hasattr(ctx, "variableDeclaration") and ctx.variableDeclaration():
            # Caso: for (let i = 0; ...)
            vdecl = ctx.variableDeclaration()
            self.visit(vdecl)
            init_done = True
        elif hasattr(ctx, "expressionList") and ctx.expressionList():
            # Caso: for (i = 0; ...)
            expr_list = ctx.expressionList(0)
            self.visit(expr_list)
            init_done = True


        cond_node = None
        post_node = None
        num_exprs = 0
        if hasattr(ctx, "expression"):
            try:
                num_exprs = len(ctx.expression())
                if num_exprs == 3:
                    cond_node = ctx.expression(1)
                    post_node = ctx.expression(2)
                elif num_exprs == 2:
                    cond_node = ctx.expression(0)
                    post_node = ctx.expression(1)
                elif num_exprs == 1:
                    cond_node = ctx.expression(0)
            except Exception:
                pass

        self.quadruple_table.insert_into_table("label", None, None, start_lbl + ":")

        # Evaluar condición
        if cond_node is not None:
            cond_val = self.visit(cond_node)
            self.quadruple_table.insert_into_table("if", cond_val, "goto", body_lbl)
            self.quadruple_table.insert_into_table("goto", after_lbl, None, None)
        else:
            # Sin condición → loop infinito
            self.quadruple_table.insert_into_table("goto", body_lbl, None, None)

        self.quadruple_table.insert_into_table("label", None, None, body_lbl + ":")


        if getattr(ctx, "block", None) and ctx.block():
            self.visit(ctx.block())


        self.quadruple_table.insert_into_table("label", None, None, update_lbl + ":")
        if post_node is not None:
            self.visit(post_node)


        self.quadruple_table.insert_into_table("goto", start_lbl, None, None)
        self.quadruple_table.insert_into_table("label", None, None, after_lbl + ":")
        self.symbol_table = old_table
        self.reset_temporal_counter()
        return None

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
        if ctx.expression():
            value = self.visit(ctx.expression())
            self.quadruple_table.insert_into_table("RETURN", value, None, None)
        self.quadruple_table.insert_into_table("endfunc", None, None, None)


    # Visit a parse tree produced by CompiscriptParser#tryCatchStatement.
    def visitTryCatchStatement(self, ctx:CompiscriptParser.TryCatchStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#switchStatement.
    def visitSwitchStatement(self, ctx:CompiscriptParser.SwitchStatementContext):
        ln = self.get_line_number(ctx)
        end_lbl = f"L{ln}_end"
        switch_node = None
        try:
            if hasattr(ctx, "expression") and len(ctx.expression()) > 0:
                switch_node = ctx.expression(0)
            else:
                switch_node = ctx.getChild(2)
        except Exception:
            switch_node = None

        switch_val = None
        try:
            if switch_node is not None:
                switch_val = self.visit(switch_node)
        except Exception:
            switch_val = None

        cases = []
        default_case = None
        if hasattr(ctx, "switchCase"):
            sc_list = ctx.switchCase()
            if not isinstance(sc_list, list):
                sc_list = [sc_list]
            cases = sc_list
        if hasattr(ctx, "defaultCase"):
            dc = ctx.defaultCase()
            if isinstance(dc, list) and len(dc) > 0:
                default_case = dc[0]
            elif dc:
                default_case = dc

        found_cases = []
        try:
            txt = ctx.getText()
            import re
            m = re.search(r"switch\s*\(\s*([^\)]+)\s*\)", txt, re.DOTALL)
            switch_txt = m.group(1).strip() if m else None
            found_cases = re.findall(r"case\s*([^:]+)\s*:", txt, re.DOTALL)
            if switch_val is None and switch_txt:
                switch_val = switch_txt
        except Exception:
            switch_txt = None
            found_cases = []

        produced = False
        for i, case_ctx in enumerate(cases):
            case_lbl = f"L{ln}_case{i}"
            case_val = None
            try:
                if hasattr(case_ctx, "expression") and len(case_ctx.expression()) > 0:
                    case_val = self.visit(case_ctx.expression(0))
            except Exception:
                case_val = None
            if case_val is None and i < len(found_cases):
                case_val = found_cases[i].strip()
            if case_val is None or switch_val is None:
                continue
            cmp_temp = self.temporal_generator()
            self.quadruple_table.insert_into_table("==", switch_val, case_val, cmp_temp)
            self.quadruple_table.insert_into_table("if", cmp_temp, "goto", case_lbl)
            produced = True

        if not produced and found_cases and switch_val is not None:
            for i, cv in enumerate(found_cases):
                case_lbl = f"L{ln}_case{i}"
                cmp_temp = self.temporal_generator()
                self.quadruple_table.insert_into_table("==", switch_val, cv.strip(), cmp_temp)
                self.quadruple_table.insert_into_table("if", cmp_temp, "goto", case_lbl)
            produced = True

        if default_case is not None:
            default_lbl = f"L{ln}_default"
            self.quadruple_table.insert_into_table("goto", default_lbl, None, None)
        else:
            self.quadruple_table.insert_into_table("goto", end_lbl, None, None)

        case_labels = [f"L{ln}_case{i}" for i in range(max(len(cases), len(found_cases)))]
        for i, case_ctx in enumerate(cases):
            case_lbl = case_labels[i]
            self.quadruple_table.insert_into_table("label", None, None, case_lbl + ":")
            old_table = self.symbol_table
            scope_key = f"case_{ln}_{i}"
            if hasattr(old_table, "scope_map") and scope_key in old_table.scope_map:
                self.symbol_table = old_table.scope_map[scope_key]
            if hasattr(case_ctx, "block") and case_ctx.block():
                self.visit(case_ctx.block())
            else:
                try:
                    if hasattr(case_ctx, "statement"):
                        st = case_ctx.statement()
                        if isinstance(st, list):
                            for s in st:
                                self.visit(s)
                        else:
                            self.visit(st)
                except Exception:
                    pass
            self.symbol_table = old_table
            self.quadruple_table.insert_into_table("goto", end_lbl, None, None)

        if default_case is not None:
            default_lbl = f"L{ln}_default"
            self.quadruple_table.insert_into_table("label", None, None, default_lbl + ":")
            old_table = self.symbol_table
            scope_key = f"default_{ln}"
            if hasattr(old_table, "scope_map") and scope_key in old_table.scope_map:
                self.symbol_table = old_table.scope_map[scope_key]
            if hasattr(default_case, "block") and default_case.block():
                self.visit(default_case.block())
            else:
                try:
                    if hasattr(default_case, "statement"):
                        st = default_case.statement()
                        if isinstance(st, list):
                            for s in st:
                                self.visit(s)
                        else:
                            self.visit(st)
                except Exception:
                    pass
            self.symbol_table = old_table
            self.quadruple_table.insert_into_table("goto", end_lbl, None, None)

        self.quadruple_table.insert_into_table("label", None, None, end_lbl + ":")
        self.reset_temporal_counter()
        return None


    # Visit a parse tree produced by CompiscriptParser#defaultCase.
    def visitDefaultCase(self, ctx:CompiscriptParser.DefaultCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by CompiscriptParser#functionDeclaration.
    def visitFunctionDeclaration(self, ctx:CompiscriptParser.FunctionDeclarationContext):
        func_name = ctx.Identifier().getText()
        params = 0
        param_name = []
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                param_name.append(param_ctx.Identifier().getText())
                params+=1
        type = self.symbol_table.elements[func_name].type

        self.quadruple_table.insert_into_table("FUNC", func_name, params, type)
        for i in param_name:
            self.quadruple_table.insert_into_table("param", i, None, None)
        # Entrar a un nuevo scope

        old_table = self.symbol_table
        self.symbol_table = old_table.scope_map["function_" + func_name]
        if ctx.block():
            self.visit(ctx.block())
        self.symbol_table = old_table
        self.reset_temporal_counter()
        return func_name


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
        return self.visit(ctx.assignmentExpr())


    # Visit a parse tree produced by CompiscriptParser#AssignExpr.
    def visitAssignExpr(self, ctx:CompiscriptParser.AssignExprContext):

        if ctx.lhs and ctx.assignmentExpr():
            left = self.visit(ctx.leftHandSide())   
            right = self.visit(ctx.assignmentExpr())
            self.quadruple_table.add("=", right, None, left)
            return left
        # ExprNoAssign (condicional)
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
        if len(ctx.logicalAndExpr()) == 1:
            return self.visit(ctx.logicalAndExpr(0))
        left = self.visit(ctx.logicalAndExpr(0))
        for i in range(1, len(ctx.logicalAndExpr())):
            op = ctx.getChild(2*i - 1).getText()  
            right = self.visit(ctx.logicalAndExpr(i))
            temp = self.temporal_generator()
            self.quadruple_table.insert_into_table(op, left, right, temp)
            left = temp
        return left


    # Visit a parse tree produced by CompiscriptParser#logicalAndExpr.
    def visitLogicalAndExpr(self, ctx:CompiscriptParser.LogicalAndExprContext):
        if len(ctx.equalityExpr()) == 1:
            return self.visit(ctx.equalityExpr(0))
        left = self.visit(ctx.equalityExpr(0))
        for i in range(1, len(ctx.equalityExpr())):
            op = ctx.getChild(2*i - 1).getText()  
            right = self.visit(ctx.equalityExpr(i))
            temp = self.temporal_generator()
            self.quadruple_table.insert_into_table(op, left, right, temp)
            left = temp
        return left


    # Visit a parse tree produced by CompiscriptParser#equalityExpr.
    def visitEqualityExpr(self, ctx:CompiscriptParser.EqualityExprContext):
        if len(ctx.relationalExpr()) == 1:
            return self.visit(ctx.relationalExpr(0))
        left = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            op = ctx.getChild(2*i - 1).getText()  
            right = self.visit(ctx.relationalExpr(i))
            temp = self.temporal_generator()
            self.quadruple_table.insert_into_table(op, left, right, temp)
            left = temp
        return left


    # Visit a parse tree produced by CompiscriptParser#relationalExpr.
    def visitRelationalExpr(self, ctx:CompiscriptParser.RelationalExprContext):
        if len(ctx.additiveExpr()) == 1:
            return self.visit(ctx.additiveExpr(0))
        left = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            op = ctx.getChild(2*i - 1).getText()  
            right = self.visit(ctx.additiveExpr(i))
            temp = self.temporal_generator()
            self.quadruple_table.insert_into_table(op, left, right, temp)
            left = temp
        return left


    # Visit a parse tree produced by CompiscriptParser#additiveExpr.
    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):

        if len(ctx.multiplicativeExpr()) == 1:
            return self.visit(ctx.multiplicativeExpr(0))
        left = self.visit(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            op = ctx.getChild(2*i - 1).getText()  
            right = self.visit(ctx.multiplicativeExpr(i))
            temp = self.temporal_generator()
            self.quadruple_table.insert_into_table(op, left, right, temp)
            left = temp
        return left


    # Visit a parse tree produced by CompiscriptParser#multiplicativeExpr.
    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        if len(ctx.unaryExpr()) == 1:
            return self.visit(ctx.unaryExpr(0))
        left = self.visit(ctx.unaryExpr(0))
        for i in range(1, len(ctx.unaryExpr())):
            op = ctx.getChild(2*i - 1).getText()  # '*', '/', '%'
            right = self.visit(ctx.unaryExpr(i))
            temp = self.temporal_generator()
            self.quadruple_table.insert_into_table(op, left, right, temp)
            left = temp
        return left


    # Visit a parse tree produced by CompiscriptParser#unaryExpr.
    def visitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        # Si hay solo un hijo, pasa al primary
        if ctx.getChildCount() == 1:
            return self.visit(ctx.primaryExpr())
        # Si hay un operador unario
        op = ctx.getChild(0).getText()
        value = self.visit(ctx.unaryExpr())
        temp = self.quadruple_table.new_temp()
        self.quadruple_table.add(op, value, None, temp)
        return temp


    # Visit a parse tree produced by CompiscriptParser#primaryExpr.
    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.expression():
            return self.visit(ctx.expression())  # paréntesis
        elif ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        elif ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())

    # Visit a parse tree produced by CompiscriptParser#literalExpr.
    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        return ctx.getText()


    # Visit a parse tree produced by CompiscriptParser#leftHandSide.
    def visitLeftHandSide(self, ctx:CompiscriptParser.LeftHandSideContext):
        if len(ctx.suffixOp()) == 0:
            return self.visit(ctx.primaryAtom())
        return self.visit(ctx.primaryAtom())  # placeholder para llamadas/indexaciones


    # Visit a parse tree produced by CompiscriptParser#IdentifierExpr.
    def visitIdentifierExpr(self, ctx:CompiscriptParser.IdentifierExprContext):
        return ctx.Identifier().getText()


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
