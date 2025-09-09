class Register:
    def __init__(self, lexeme, identifier, type, scope, line_pos, is_mutable, kind, params, return_type, parent_class, dim, supported_types):
        self.lexeme = lexeme
        self.identifier = identifier #Nombre de l función, variable o clase 
        self.type = type # Integer, String, Boolean o Null, si es una función entonces es None
        self.scope = scope
        self.line_pos = line_pos
        self.is_mutable = is_mutable #Si es una const entonces es false 
        self.kind = kind #Variable, función, proceso, etc. 
        
        # Solo válidos para funciones 
        self.params = params 
        self.return_type = return_type

        #Solo para clases 

        self.parent_class = parent_class #Indica de quien se hereda 
         
        # Solo para arrays

        self.dim = dim #Si es 1, es un array 1D, si es 2 es un array 2D

"""
Consideraciones: cualquier variable o función dentro de el ámbito de una clase se v a considerar como un atributo o método de la clase 
"""
class Symbol_table():
    def __init__(self, parent = None, scope = "Global"):
        self.elements = {}
        self.parent = parent
        self.children = [] #Guarda los elementos hijos
        self.scope = "Global" if parent is None else scope

    def insert_value(self, lexeme, identifier, type, scope, line_pos, is_mutable, kind, params, return_type):
        if identifier in self.elements.keys():
            print("ERROR: redeclaración, no puedes hacer redeclaraciones")
        self.elements[identifier] = Register(lexeme, identifier, type, scope, line_pos, is_mutable, kind, params, return_type)

    def lookup_local(self, identifier):
        return self.elements.get(identifier)
    
    def lookup_global(self, identifier):
        current_table = self
        while current_table:
            if identifier in current_table.elements:
                return current_table.elements[identifier]
            current_table = current_table.parent
        return None
    
    def create_child_scope(self, scope_name):
        return Symbol_table(parent=self, scope_name=scope_name)

    def update_value(self, identifier):
        pass
    def loopkup(self):
        pass

    def search_value(self, identifier):
        if identifier in self.elements.keys():
            return True
        else: 
            False

class CompilerScriptSymbolManager:
    def __init__(self):
        self.global_table = Symbol_table()
        self.current_table = self.global_table
        self.scope_stack = [self.global_table]
    
    def enter_scope(self, scope_name):
        """Entra a un nuevo ámbito"""
        new_table = self.current_table.create_child_scope(scope_name)
        self.current_table = new_table
        self.scope_stack.append(new_table)
        return new_table
    
    def exit_scope(self):
        """Sale del ámbito actual"""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_table = self.scope_stack[-1]
        return self.current_table
    
    def declare_variable(self, name, var_type=None, is_const=False, value=None, line_pos=None):
        """Declara una variable en el ámbito actual"""
        return self.current_table.insert_symbol(
            lexeme=name,
            identifier=name,
            type=var_type,
            line_pos=line_pos,
            is_mutable=not is_const,
            kind="variable",
            value=value
        )
    
    def declare_function(self, name, params, return_type=None, line_pos=None):
        """Declara una función"""
        return self.current_table.insert_symbol(
            lexeme=name,
            identifier=name,
            line_pos=line_pos,
            kind="function",
            params=params,
            return_type=return_type
        )
    
    def declare_class(self, name, parent_class=None, line_pos=None):
        """Declara una clase"""
        return self.current_table.insert_symbol(
            lexeme=name,
            identifier=name,
            line_pos=line_pos,
            kind="class",
            parent_class=parent_class
        )
    
    def declare_array(self, name, array_type, dimensions=1, is_const=False, line_pos=None):
        """Declara un array"""
        return self.current_table.insert_symbol(
            lexeme=name,
            identifier=name,
            type=array_type,
            line_pos=line_pos,
            is_mutable=not is_const,
            kind="variable",
            dim=dimensions
        )

