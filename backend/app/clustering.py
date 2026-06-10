def hamming_distance(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def cluster_by_hamming(
    hashes: dict[int, str], threshold: int
) -> list[list[int]]:
    """Group photo ids whose perceptual hashes are within `threshold` bits.

    Builds connected components with union-find over all pairs. All-pairs is
    O(n^2) but fine for a few thousand images; a BK-tree over the hashes is
    the scaling path beyond that.
    """
    ids = list(hashes)
    values = {i: int(hashes[i], 16) for i in ids}
    parent = {i: i for i in ids}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for idx, a in enumerate(ids):
        for b in ids[idx + 1:]:
            if (values[a] ^ values[b]).bit_count() <= threshold:
                parent[find(a)] = find(b)

    groups: dict[int, list[int]] = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())
