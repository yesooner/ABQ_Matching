import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def install_abaqus_stubs():
    abaqus = types.ModuleType("abaqus")
    abaqus.mdb = types.SimpleNamespace(models={})
    sys.modules["abaqus"] = abaqus

    constants = types.ModuleType("abaqusConstants")
    for name, value in {
        "FIXED_DOF": "FIXED_DOF",
        "ON": True,
        "OFF": False,
        "IMPRINT": "IMPRINT",
        "OFF_CONST": False,
    }.items():
        setattr(constants, name, value)
    constants.OFF = False
    sys.modules["abaqusConstants"] = constants

    region_toolset = types.ModuleType("regionToolset")
    region_toolset.Region = lambda **kwargs: kwargs
    sys.modules["regionToolset"] = region_toolset


def load_kernel():
    install_abaqus_stubs()
    spec = importlib.util.spec_from_file_location(
        "ABQ_Matching_kernel", str(ROOT / "ABQ_Matching_kernel.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Node:
    def __init__(self, label, coordinates, instance_name="Part-1-1"):
        self.label = label
        self.coordinates = coordinates
        self.instanceName = instance_name


class KeywordBlock:
    def __init__(self, blocks):
        self.sieBlocks = list(blocks)

    def synchVersions(self, storeNodesAndElements=False):
        return None

    def replace(self, index, text):
        self.sieBlocks[index] = text


class KernelSmokeTests(unittest.TestCase):
    def test_match_nodes_matches_every_master_once_and_leaves_extra_slave_nodes(self):
        kernel = load_kernel()
        masters = [
            Node(1, (0.0, 0.0, 0.0)),
            Node(2, (10.0, 0.0, 0.0)),
        ]
        slaves = [
            Node(10, (0.1, 0.0, 0.0)),
            Node(11, (10.1, 0.0, 0.0)),
            Node(12, (100.0, 0.0, 0.0)),
        ]

        pairs = kernel._match_nodes(masters, slaves)

        self.assertEqual([(0, 0), (1, 1)], [(a, b) for a, b, _ in pairs])
        self.assertEqual(2, len({slave for _, slave, _ in pairs}))

    def test_match_nodes_expands_candidate_search_when_initial_candidates_conflict(self):
        kernel = load_kernel()
        kernel.INITIAL_K = 1
        kernel.MAX_K = 2
        masters = [
            Node(1, (0.0, 0.0, 0.0)),
            Node(2, (0.01, 0.0, 0.0)),
        ]
        slaves = [
            Node(10, (0.0, 0.0, 0.0)),
            Node(11, (1.0, 0.0, 0.0)),
        ]

        pairs = kernel._match_nodes(masters, slaves)

        self.assertEqual(2, len(pairs))
        self.assertEqual(2, len({slave for _, slave, _ in pairs}))

    def test_assign_from_candidates_improves_greedy_pair_that_causes_long_match(self):
        kernel = load_kernel()
        candidates = [
            [(1.0, 0), (2.0, 1)],
            [(1.1, 0), (100.0, 1)],
        ]

        pairs, failed = kernel._assign_from_candidates(candidates)

        self.assertEqual([], failed)
        self.assertEqual([(0, 1), (1, 0)], [(a, b) for a, b, _ in pairs])
        self.assertLess(sum(distance for _, _, distance in pairs), 4.0)

    def test_cleanup_old_matching_keywords_removes_whole_conflicts_block(self):
        kernel = load_kernel()
        model = types.SimpleNamespace(keywordBlock=KeywordBlock([
            "*End Assembly",
            "*Conflicts, Generated keywords",
            "*Connector Behavior, name=ConnSect-1",
            "*Connector Elasticity, component=1",
            "10.,",
            "*Conflicts, User edited keywords",
            "*Conflicts, End of conflict block",
            "*Material, name=Material-1",
        ]))

        kernel._cleanup_old_matching_keywords(model)

        remaining = "\n".join(model.keywordBlock.sieBlocks)
        self.assertNotIn("*Conflicts", remaining)
        self.assertNotIn("*Connector Behavior, name=ConnSect-1", remaining)
        self.assertIn("*Material, name=Material-1", remaining)


if __name__ == "__main__":
    unittest.main()
