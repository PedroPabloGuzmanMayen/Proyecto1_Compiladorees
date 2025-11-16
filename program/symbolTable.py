import sys

class Register:
    def __init__(self, identifier, type, scope, line_pos, is_mutable, kind, params=None, return_type=None, parent_class=None, dim=None, has_constructor=False, constructor_params=None):
        self.identifier = identifier
        self.type = type
        self.scope = scope
        self.line_pos = line_pos
        self.is_mutable = is_mutable
        self.kind = kind
        self.params = params or []
        self.return_type = return_type
        self.parent_class = parent_class
        self.has_constructor = has_constructor
        self.constructor_params = constructor_params or []
        self.members = {} if kind == "class" else None
        self.dim = dim
        self.address = 0

    def update_memory_address(self, relative_memor_addr):
        self.address = relative_memor_addr


class Symbol_table:
    def __init__(self, parent=None, scope="Global"):
        self.elements = {}
        self.parent = parent
        self.children = []
        self.scope = "Global" if parent is None else scope
        self.scope_map = {}

    def insert_symbol(self, identifier, type, scope, line_pos, is_mutable, kind, params=None, return_type=None, parent_class=None, dim=None):
        if identifier in self.elements:
            return False
        reg = Register(identifier, type, scope, line_pos, is_mutable, kind, params or [], return_type, parent_class, dim)
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

    def add_class_member(self, class_name, member_reg):
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

    def add_address(self, symbol_name, address):
        if symbol_name in self.elements:
            self.elements[symbol_name].update_memory_address(address)

    def add_addres(self, symbol_name, address):
        self.add_address(symbol_name, address)

    def print_table(self, output=sys.stdout, indent=0):
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
        for child in getattr(self, "children", []):
            child.print_table(output=output, indent=indent + 1)

