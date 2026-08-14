import pandapower.networks as pn


net = pn.case33bw()


print("=== IEEE 33-BUS BASIC INFO ===")
print("Number of buses:", len(net.bus))
print("Number of loads:", len(net.load))
print("Number of lines:", len(net.line))
print("Number of generators:", len(net.gen))
print("Number of external grids:", len(net.ext_grid))

print("\n=== BUS TABLE ===")
print(net.bus.head(10))

print("\n=== LOAD TABLE ===")
print(net.load.head(10))

print("\n=== LINE TABLE ===")
print(net.line.head(10))