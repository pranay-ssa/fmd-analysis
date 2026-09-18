import json
mods = ["resnet18", "resnet50", "resnet50_inception", "resnet50_se"]
pc = {}
for m in mods:
    j = json.load(open(f"/home/pranayp/combined_22_runs/{m}/epochs_50/metrics.json"))
    pc[m] = j["per_class"]
classes = sorted(pc[mods[0]], key=lambda c: -pc[mods[0]][c]["support"])
short = {"resnet18": "R18", "resnet50": "R50", "resnet50_inception": "Inc", "resnet50_se": "SE"}
print("Class".ljust(44) + "  R18    R50    Inc     SE   supp")
tot = {m: [0, 0] for m in mods}  # correctly-classified counts is derivable but per-class recall avg is macro
for c in classes:
    cells = "".join(f"{pc[m][c]['recall']*100:7.1f}" for m in mods)
    print(c.ljust(44) + cells + f"  {pc[m][c]['support']}")