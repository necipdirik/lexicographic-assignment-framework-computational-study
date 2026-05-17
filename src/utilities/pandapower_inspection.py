import pandapower.networks as pn

cases = [name for name in dir(pn) if name.startswith("case")]
print(cases)