class Logged:
    def log(self, *msg):
        print('<',type(self),' ',id(self),'>\t', *msg)
