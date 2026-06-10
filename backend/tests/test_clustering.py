from app.clustering import cluster_by_hamming, hamming_distance


def test_hamming_distance_counts_differing_bits():
    assert hamming_distance("0" * 16, "0" * 16) == 0
    assert hamming_distance("0" * 16, "0" * 15 + "1") == 1
    assert hamming_distance("0" * 16, "f" * 16) == 64


def test_identical_and_near_hashes_cluster_together():
    hashes = {
        1: "8f3a5c7e9b1d2f40",
        2: "8f3a5c7e9b1d2f40",  # identical to 1
        3: "8f3a5c7e9b1d2f43",  # 2 bits from 1
        4: "70c5a3816e4d0bf2",  # far from everything
    }
    groups = cluster_by_hamming(hashes, threshold=8)
    groups = sorted([sorted(g) for g in groups])
    assert groups == [[1, 2, 3], [4]]


def test_threshold_boundary_is_inclusive():
    hashes = {1: "0" * 16, 2: "0" * 15 + "3"}  # exactly 2 bits apart
    assert len(cluster_by_hamming(hashes, threshold=2)) == 1
    assert len(cluster_by_hamming(hashes, threshold=1)) == 2


def test_transitive_chains_form_one_cluster():
    # a-b and b-c are within threshold but a-c is not; connected
    # components still group all three.
    hashes = {
        1: "0000000000000000",
        2: "0000000000000003",
        3: "000000000000000f",
    }
    assert hamming_distance(hashes[1], hashes[3]) > 2
    groups = cluster_by_hamming(hashes, threshold=2)
    assert len(groups) == 1


def test_empty_input_produces_no_clusters():
    assert cluster_by_hamming({}, threshold=8) == []
