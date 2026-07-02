values = [
2678284,
2675980,
2673676,
2669068,
2664460,
2662156,
2659852,
2657548,
]

print("Value        /16      /32      /64      /128      /256      hex")
print("-"*75)

for v in values:
    print(
        f"{v:<10}"
        f"{v//16:<10}"
        f"{v//32:<10}"
        f"{v//64:<10}"
        f"{v//128:<11}"
        f"{v//256:<11}"
        f"{hex(v)}"
    )

print("\nDifferences:")

for a, b in zip(values, values[1:]):
    print(a - b)
