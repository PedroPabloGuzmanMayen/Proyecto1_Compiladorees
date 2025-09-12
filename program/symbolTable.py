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
        

    def print_table(self, indent=0):
        print(" " * indent + f"Scope: {self.scope}")
        for identifier, reg in self.elements.items():
            print(" " * (indent + 2) + f"- {identifier}:")
            print(" " * (indent + 4) + f"Tipo: {reg.type}")
            print(" " * (indent + 4) + f"Mutable: {reg.is_mutable}")
            print(" " * (indent + 4) + f"Clase Padre: {reg.parent_class}")
            print(" " * (indent + 4) + f"Kind: {reg.kind}")
            print(" " * (indent + 4) + f"Línea: {reg.line_pos}")
            if reg.kind == "función":
                print(" " * (indent + 4) + f"Params: {reg.params}")
                print(" " * (indent + 4) + f"Return: {reg.return_type}")
            if reg.dim > 0:
                print(" " * (indent + 4) + f"Dimensión array: {reg.dim}")

        for child in self.children:
            child.print_table(indent + 2)