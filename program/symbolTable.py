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
        self.members = {} if kind == "class" else None
         
        # Solo para arrays

        self.dim = dim #Si es 1, es un array 1D, si es 2 es un array 2D
        self.address = 0
        self.size = 0

    def update_memory_address(self, relative_memor_addr):
        self.address = relative_memor_addr

        
"""
Consideraciones: cualquier variable o función dentro de el ámbito de una clase se v a considerar como un atributo o método de la clase 
"""
class Symbol_table():
    def __init__(self, parent = None, scope = "Global"):
        self.elements = {}
        self.parent = parent
        self.children = [] #Guarda los elementos hijos
        self.scope = "Global" if parent is None else scope
        self.scope_map = {}

    def insert_symbol(self,identifier, type, scope, line_pos, is_mutable, kind, params, return_type, parent_class, dim):
        if identifier in self.elements:
            return False
        reg = Register(identifier, type, scope, line_pos, is_mutable, kind, params, return_type, parent_class, dim)
        if kind == "class" and not hasattr(reg, "members"):
            reg.members = {}
        self.elements[identifier] = reg
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
        self.scope_map[scope_name] = child
        return child
    
    
    def add_class_member(self, class_name, member_reg: Register):
        """
        Adjunta un miembro (campo o método) al registro de la clase dada.
        Devuelve True si se pudo, False en caso de error o duplicado.
        """
        cls = self.lookup_global(class_name)
        if not cls or cls.kind != "class":
            return False
        if cls.members is None:
            cls.members = {}
        if member_reg.identifier in cls.members:
            return False
        cls.members[member_reg.identifier] = member_reg
        return True

    def get_class_member(self, class_name, member_name):
        cls = self.lookup_global(class_name)
        if not cls or cls.kind != "class" or not cls.members:
            return None
        return cls.members.get(member_name)
    
    def add_addres(self, symbol_name, address):
        self.elements[symbol_name].update_memory_address(address)
        

    def print_table(self, output=sys.stdout, indent=0):
        """Imprime la tabla de símbolos y sus subtablas en formato jerárquico"""
        indent_str = "  " * indent
        print(f"{indent_str}Scope: {self.scope}", file=output)

        if not self.elements:
            print(f"{indent_str}  (sin símbolos)", file=output)

        for sym in self.elements.values():
            print(f"{indent_str}  - {sym.identifier}:", file=output)
            print(f"{indent_str}      Tipo: {sym.type}", file=output)
            print(f"{indent_str}      Dimensión: {sym.dim}", file=output)
            print(f"{indent_str}      Mutable: {sym.is_mutable}", file=output)
            print(f"{indent_str}      Clase Padre: {sym.parent_class}", file=output)
            print(f"{indent_str}      Kind: {sym.kind}", file=output)
            print(f"{indent_str}      Línea: {sym.line_pos}", file=output)

        # Recorrer scopes hijos
        for child in getattr(self, "children", []):
            child.print_table(output=output, indent=indent + 1)
