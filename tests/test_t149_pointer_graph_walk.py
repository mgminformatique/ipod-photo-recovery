from pathlib import Path
import struct
from collections import defaultdict, deque

FILE = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def page_vals(data, page):
    return [u16(data, page + i * 2) for i in range(128)]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 POINTER GRAPH WALK")
    print("=" * 100)

    pages = list(range(0x0000, len(data) & ~0xff, 0x100))
    graph = defaultdict(list)

    for page in pages:
        vals = page_vals(data, page)
        for idx, v in enumerate(vals):
            if v % 0x100 == 0 and 0x5700 <= v < len(data):
                graph[page].append((idx, v))

    roots = [0x5700, 0x5f00, 0x6200, 0x7700, 0x7800, 0x7900]

    for root in roots:
        print()
        print("-" * 100)
        print(f"ROOT 0x{root:04x}")

        seen = set()
        q = deque([(root, 0)])

        while q:
            node, depth = q.popleft()
            if node in seen or depth > 4:
                continue
            seen.add(node)

            edges = graph.get(node, [])
            print(f"{'  '*depth}0x{node:04x} edges={len(edges)}")

            targets = []
            for idx, target in edges[:40]:
                targets.append(target)
                print(f"{'  '*depth}  [{idx:03d}] -> 0x{target:04x}")

            for target in targets:
                if target not in seen:
                    q.append((target, depth + 1))

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"pages with edges: {len(graph)}")

    top = sorted(graph.items(), key=lambda x: len(x[1]), reverse=True)[:40]
    for page, edges in top:
        print(f"0x{page:04x} edges={len(edges)}")

if __name__ == "__main__":
    main()
