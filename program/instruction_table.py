class Quadruple():
    def __init__(self):
        self.temp_counter = 0
        self.quadruples = []

    def temp_reset(self):
        self.temp_counter = 0

    def insert_into_table(self, operator, arg1, arg2, temp):
        self.quadruples.append((operator, arg1, arg2, temp + str(self.temp_counter) ))
        self.temp_counter +=1 

    def write_to_console(self):
        pass

