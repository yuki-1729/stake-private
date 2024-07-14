class MinesCalc:
    @staticmethod
    def factorial(num):
        val = num

        i = num
        while i > 1:
            val *= i - 1
            i -= 1

        return val
    
    @staticmethod
    def combination(x, y):
        if(x == y):
            return 1
        return MinesCalc.factorial(x) / (MinesCalc.factorial(y) * MinesCalc.factorial(x - y))

    @staticmethod
    def calc_multiplier(bomb, gem):
        n = 25
        x = 25 - bomb

        first = MinesCalc.combination(n, gem)
        second = MinesCalc.combination(x, gem)
        
        _result = 0.99*(first/second)
        result = round(_result*100)/100
        
        return result