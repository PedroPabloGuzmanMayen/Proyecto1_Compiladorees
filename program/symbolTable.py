import sys
class Register:
    def __init__(self, identifier, type, scope, line_pos, is_mutable, kind, params, return_type, parent_class, dim, has_constructor = False, constructor_params = []):
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
        self.has_constructor = has_constructor
        self.constructor_params = constructor_params
         
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

    def insert_symbol(self,identifier, type, scope, line_pos, is_mutable, kind, params, return_type, parent_class, dim):
        if identifier in self.elements.keys():
            return False
        self.elements[identifier] = Register(identifier, type, scope, line_pos, is_mutable, kind, params, return_type, parent_class, dim)
        return True

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
        child = Symbol_table(parent=self, scope=scope_name)
        self.children.append(child)
        return child
        

    def print_table(self, output=sys.stdout):
        for sym in self.elements.values():
            print(f"  - {sym.identifier}:")
            print(f"      Tipo: {sym.type}")
            print(f"      Dimensión: {sym.dim}")
            print(f"      Mutable: {sym.is_mutable}")
            print(f"      Clase Padre: {sym.parent_class}")
            print(f"      Kind: {sym.kind}")
            print(f"      Línea: {sym.line_pos}")
