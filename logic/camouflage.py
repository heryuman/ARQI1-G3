from config import CAMOUFLAGE_SEQUENCE

def sequence_ok(seq):
    return seq[-3:] == CAMOUFLAGE_SEQUENCE
