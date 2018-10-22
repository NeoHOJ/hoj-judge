
'''
a small utility that does the fundemental "tolerant" judge; from JudgeGirl's data
'''
def tolerantDiffAt(fa, fb):
    def rstrip(s):
        while s and (s[-1] == '\r' or s[-1] == '\n'): s = s[:-1]
        return s

    line = 0
    while True:
        line += 1
        la, lb = fa.readline(), fb.readline()
        if la:
            if not lb or rstrip(la.strip()) != rstrip(lb.strip()): return line
        elif lb:
            return line
        else:
            break
    return -1
