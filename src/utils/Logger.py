class Logged:
    def log(self, *msg):
        print(f'<{type(self)} {id(self)}>\t', *msg)
