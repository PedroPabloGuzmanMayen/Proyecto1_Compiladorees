class RegInfo:
    def __init__(self, name):
        self.name = name
        self.content = None   
        self.last_use = 0
        self.dirty = False     
        self.home = None        

class RegisterAllocator:
    def __init__(self):
        t_regs = [f"$t{i}" for i in range(10)]  
        s_regs = [f"$s{i}" for i in range(8)]    
        self.pool = [RegInfo(r) for r in t_regs + s_regs]
        self._time = 0
        self.stack_offset = 0  
        self.spill_map = {}     
        self.reserve_spill_base = 0  

    def _touch(self, reginfo):
        self._time += 1
        reginfo.last_use = self._time

    def find_by_content(self, name):
        for r in self.pool:
            if r.content == name:
                self._touch(r)
                return r
        return None

    def get_reg_for(self, name, prefer_s=False):
        r = self.find_by_content(name)
        if r:
            return r.name
        # Buscar registro libre
        for r in self.pool:
            if r.content is None:
                r.content = name
                r.dirty = False
                r.home = name
                self._touch(r)
                return r.name
        victim = min(self.pool, key=lambda x: x.last_use)
        self.spill(victim)
        victim.content = name
        victim.dirty = False
        victim.home = name
        self._touch(victim)
        return victim.name

    def free_reg_by_name(self, reg_name, store=False):
        for r in self.pool:
            if r.name == reg_name:
                if store and r.content:
                    self._spill_to_stack(r.content, r.name)
                r.content = None
                r.dirty = False
                r.home = None
                return True
        return False

    def mark_dirty(self, reg_name):
        for r in self.pool:
            if r.name == reg_name:
                r.dirty = True
                self._touch(r)
                return

    def spill(self, reginfo):
        if not reginfo.content:
            reginfo.content = None
            reginfo.dirty = False
            reginfo.home = None
            return
        name = reginfo.content
        self._spill_to_stack(name, reginfo.name)
        reginfo.content = None
        reginfo.dirty = False
        reginfo.home = None

    def _spill_to_stack(self, name, reg_name):
        if name in self.spill_map:
            return
        off = self.stack_offset
        self.stack_offset += 4
        self.spill_map[name] = off

    def has_spill(self, name):
        return name in self.spill_map

    def get_spill_offset(self, name):
        return self.spill_map.get(name)

    def set_spill_base(self, base):
        self.reserve_spill_base = base

    def total_spill_bytes(self):
        return self.stack_offset
