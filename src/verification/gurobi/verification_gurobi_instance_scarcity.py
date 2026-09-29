R = ["r1", "r2"]

N = ["n1", "n2", "n3"]

C = ["critical", "vulnerable"]

H = ["n1"]

a = {
    ("r1", "n1"): 1,
    ("r1", "n2"): 1,
    ("r1", "n3"): 0,

    ("r2", "n1"): 1,
    ("r2", "n2"): 0,
    ("r2", "n3"): 1,
}

s = {
    ("r1", "n1"): 1,
    ("r1", "n2"): 0,
    ("r1", "n3"): 0,

    ("r2", "n1"): 0,
    ("r2", "n2"): 0,
    ("r2", "n3"): 1,
}

b = {
    ("n1", "critical"): 1,
    ("n1", "vulnerable"): 0,

    ("n2", "critical"): 0,
    ("n2", "vulnerable"): 1,

    ("n3", "critical"): 0,
    ("n3", "vulnerable"): 1,
}

w = {
    "critical": 2,
    "vulnerable": 1,
}