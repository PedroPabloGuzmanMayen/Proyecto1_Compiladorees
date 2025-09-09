class Register:
    def __init__(self, lexeme, identifier, type, scope, line_pos, is_mutable, kind, params, return_type, parent_class):
        self.lexeme = lexeme
        self.identifier = identifier
        self.type = type # Integer, String, Boolean o Null, si es una función entonces es None
        self.scope = scope
        self.line_pos = line_pos
        self.is_mutable = is_mutable #Si es una const entonces es false 
        self.kind = kind #Variable, función, proceso, etc. 
        
        # Solo válidos para funciones 
        self.params = params 
        self.return_type = return_type

        #Solo para clases 

        self.inhereit = parent_class #Indica de quien se hereda 


"""
Consideraciones: cualquier variable o función dentro de el ámbito de una clase se v a considerar como un atributo o método de la clase 
"""
class Symbol_table():
    def __init__(self, parent = None, scope = None):
        self.elements = {}
        self.parent = parent

        self.scope = "Global" if parent is None else scope

    def insert_value(self, lexeme, identifier, type, scope, line_pos, is_mutable, kind, params, return_type):
        if identifier in self.elements.keys():
            print("ERROR: redeclaración, no puedes hacer redeclaraciones")
        self.elements[identifier] = Register(lexeme, identifier, type, scope, line_pos, is_mutable, kind, params, return_type)

    def update_value(self):
        pass
    def loopkup(self):
        pass

    def search_value(self, identifier):
        pass

