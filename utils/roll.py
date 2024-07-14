from utils.generate import generate_value

class Roller:
    @staticmethod
    def calc_multiplier(target, condition):
        if condition == "below":
            chance = (target - 1) / 100
        else:
            chance = (100 - target) / 100

        return (1 / chance) * (1 - 0.01)
    
    @staticmethod
    def calc_payout(bet, multiplier):
        return bet * multiplier
    
    @staticmethod
    def roll(seed_pair, target, condition, bet):
        multiplier = Roller.calc_multiplier(target, condition)
        payout = Roller.calc_payout(bet, multiplier)

        result = generate_value(seed_pair["server"], seed_pair["client"], seed_pair["nonce"], "dice")
        if (condition == "below" and result < target) or (condition == "above" and result > target):
            return True, result, multiplier, payout
        else:
            return False, result, 0, 0