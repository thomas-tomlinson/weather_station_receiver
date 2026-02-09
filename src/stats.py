class STATS:
    def __init__(self):
        self.data = {}

    def change(self, statname, value):
        if self.add_counter(statname):
            self.data[statname] += value
        else:
            raise ValueError('statname not initialized')

    def add_counter(self, statname):
        if type(statname) is not str:
            raise ValueError('counter name must be a string')
        if statname in self.data.keys():
            return True
        else:
            self.data[statname] = 0
            return False

    def add_counters(self, statnames):
        if type(statnames) is not list:
            raise ValueError('add_counters requires a list argument')
        for sname in statnames:
            self.add_counter(sname)

    def get_counters(self):
        return self.data

