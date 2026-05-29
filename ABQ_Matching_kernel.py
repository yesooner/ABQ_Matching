# -*- coding: utf-8 -*-
from __future__ import print_function

from abaqus import *
from abaqusConstants import *
import regionToolset
import math

try:
    import connectorBehavior
except:
    connectorBehavior = None


DEFAULT_SPRING_STIFFNESS = 1000.0
INITIAL_K = 5
MAX_K = 20


def _clean_text(value, field_name):
    if value is None:
        raise ValueError('%s is required.' % field_name)
    text = str(value).strip()
    if not text:
        raise ValueError('%s is required.' % field_name)
    return text


def _get_model_and_sets(modelName, setMaster, setSlave):
    modelName = _clean_text(modelName, 'Model-Name')
    setMaster = _clean_text(setMaster, 'Set-Master')
    setSlave = _clean_text(setSlave, 'Set-Slave')

    if modelName not in mdb.models.keys():
        raise ValueError('Model not found: %s' % modelName)

    model = mdb.models[modelName]
    assembly = model.rootAssembly

    if setMaster not in assembly.sets.keys():
        raise ValueError('Assembly node set not found: %s' % setMaster)
    if setSlave not in assembly.sets.keys():
        raise ValueError('Assembly node set not found: %s' % setSlave)

    master_nodes = assembly.sets[setMaster].nodes
    slave_nodes = assembly.sets[setSlave].nodes

    if len(master_nodes) == 0:
        raise ValueError('Set-Master has no nodes: %s' % setMaster)
    if len(slave_nodes) == 0:
        raise ValueError('Set-Slave has no nodes: %s' % setSlave)
    if len(slave_nodes) < len(master_nodes):
        raise ValueError('Set-Slave node count must be >= Set-Master node count.')

    return model, assembly, master_nodes, slave_nodes


def _node_coords(nodes):
    coords = []
    for node in nodes:
        c = node.coordinates
        coords.append((float(c[0]), float(c[1]), float(c[2])))
    return coords


def _distance(c1, c2):
    return math.sqrt(
        (c1[0] - c2[0]) ** 2 +
        (c1[1] - c2[1]) ** 2 +
        (c1[2] - c2[2]) ** 2)


def _pure_python_candidates(master_coords, slave_coords, k):
    all_candidates = []
    for c1 in master_coords:
        distances = []
        for j, c2 in enumerate(slave_coords):
            distances.append((_distance(c1, c2), j))
        distances.sort(key=lambda item: item[0])
        all_candidates.append(distances[:k])
    return all_candidates


def _kdtree_candidates(master_coords, slave_coords, k):
    try:
        from scipy.spatial import cKDTree
    except:
        return None

    tree = cKDTree(slave_coords)
    dist, idx = tree.query(master_coords, k=k)
    candidates = []
    for i in range(len(master_coords)):
        row = []
        if k == 1:
            row.append((float(dist[i]), int(idx[i])))
        else:
            for j in range(k):
                row.append((float(dist[i][j]), int(idx[i][j])))
        candidates.append(row)
    return candidates


def _assign_from_candidates(candidates):
    first_dist = []
    for i, row in enumerate(candidates):
        if row:
            first_dist.append((row[0][0], i))
        else:
            first_dist.append((float('inf'), i))
    first_dist.sort(key=lambda item: item[0])

    used = set()
    pairs = []
    failed = []
    for dist0, master_index in first_dist:
        assigned = False
        for distance, slave_index in candidates[master_index]:
            if slave_index not in used:
                used.add(slave_index)
                pairs.append((master_index, slave_index, distance))
                assigned = True
                break
        if not assigned:
            failed.append(master_index)
    return pairs, failed


def _match_nodes(master_nodes, slave_nodes):
    master_coords = _node_coords(master_nodes)
    slave_coords = _node_coords(slave_nodes)

    k = min(INITIAL_K, len(slave_nodes))
    while k <= min(MAX_K, len(slave_nodes)):
        candidates = _kdtree_candidates(master_coords, slave_coords, k)
        if candidates is None:
            candidates = _pure_python_candidates(master_coords, slave_coords, k)
        pairs, failed = _assign_from_candidates(candidates)
        if not failed:
            pairs.sort(key=lambda item: item[0])
            return pairs
        if k == len(slave_nodes):
            break
        k = min(k * 2, MAX_K, len(slave_nodes))

    candidates = _pure_python_candidates(master_coords, slave_coords, len(slave_nodes))
    pairs, failed = _assign_from_candidates(candidates)
    if failed:
        raise ValueError('Failed to match all master nodes. Failed count: %s' % len(failed))
    pairs.sort(key=lambda item: item[0])
    return pairs


def _safe_name(prefix, serialNumber):
    serial = _clean_text(serialNumber, 'Name suffix')
    serial = serial.replace(' ', '_')
    return '%s-%s' % (prefix, serial)


def _feature_name_exists(assembly, name):
    try:
        return name in assembly.features.keys()
    except:
        return False


def _engineering_name_exists(assembly, name):
    try:
        return name in assembly.engineeringFeatures.springDashpots.keys()
    except:
        return False


def _keyword_text_exists(model, marker):
    try:
        model.keywordBlock.synchVersions(storeNodesAndElements=False)
        for block in model.keywordBlock.sieBlocks:
            if marker in block:
                return True
    except:
        pass
    return False


def _unique_name(base, exists_func):
    if not exists_func(base):
        return base
    index = 2
    while True:
        name = '%s_%s' % (base, index)
        if not exists_func(name):
            return name
        index += 1


def _region_for_node(nodes, index):
    return regionToolset.Region(nodes=nodes[index:index + 1])


def _print_summary(name, pairs):
    distances = [pair[2] for pair in pairs]
    max_dist = max(distances) if distances else 0.0
    avg_dist = sum(distances) / float(len(distances)) if distances else 0.0
    print('ABQ_Matching: %s generated.' % name)
    print('ABQ_Matching: matched pairs = %s' % len(pairs))
    print('ABQ_Matching: max distance = %s' % max_dist)
    print('ABQ_Matching: average distance = %s' % avg_dist)


def spring_matching(modelName, setMaster, setSlave, serialNumber):
    model, assembly, master_nodes, slave_nodes = _get_model_and_sets(
        modelName, setMaster, setSlave)
    pairs = _match_nodes(master_nodes, slave_nodes)
    _cleanup_old_matching_keywords(model)

    base_name = _safe_name('Springs/Dashpots', serialNumber)
    name = _unique_name(base_name, lambda candidate: _engineering_name_exists(assembly, candidate))

    region_pairs = []
    for master_index, slave_index, distance in pairs:
        region_pairs.append((
            _region_for_node(master_nodes, master_index),
            _region_for_node(slave_nodes, slave_index)))

    assembly.engineeringFeatures.TwoPointSpringDashpot(
        name=name,
        regionPairs=region_pairs,
        axis=FIXED_DOF,
        dof1=2,
        dof2=2,
        orientation=None,
        springBehavior=ON,
        springStiffness=DEFAULT_SPRING_STIFFNESS,
        dashpotBehavior=OFF)

    _print_summary(name, pairs)
    assembly.regenerate()


def _node_ref(node):
    instance_name = ''
    try:
        instance_name = node.instanceName
    except:
        pass
    if instance_name:
        return '%s.%s' % (instance_name, node.label)
    return '%s' % node.label


def _element_label_base(name):
    checksum = 0
    for i, char in enumerate(name):
        checksum += (i + 1) * ord(char)
    return (100 + checksum % 800) * 1000000


def _connector_keyword_text(name, pairs, master_nodes, slave_nodes):
    lines = []
    label_base = _element_label_base(name)
    lines.append('** ABQ_Matching connector elements: %s' % name)
    lines.append('*Element, type=CONN3D2, elset=%s' % name)
    for i, pair in enumerate(pairs):
        master_index, slave_index, distance = pair
        lines.append('%s, %s, %s' % (
            label_base + i + 1,
            _node_ref(master_nodes[master_index]),
            _node_ref(slave_nodes[slave_index])))
    lines.append('*Connector Section, elset=%s' % name)
    lines.append('Cartesian,')
    lines.append('** End ABQ_Matching connector elements: %s' % name)
    return '\n'.join(lines)


def _insert_keyword_block(model, text):
    model.keywordBlock.synchVersions(storeNodesAndElements=False)
    insert_index = len(model.keywordBlock.sieBlocks) - 1
    for i, block in enumerate(model.keywordBlock.sieBlocks):
        if block.strip().lower().startswith('*end assembly'):
            insert_index = max(i - 1, 0)
            break
    if insert_index < 0:
        insert_index = 0
    model.keywordBlock.insert(insert_index, text)


def _delete_keyword_block(model, start_index, end_index):
    for i in range(end_index, start_index - 1, -1):
        try:
            model.keywordBlock.replace(i, '')
        except:
            pass


def _cleanup_old_matching_keywords(model):
    try:
        model.keywordBlock.synchVersions(storeNodesAndElements=False)
    except:
        return

    blocks = list(model.keywordBlock.sieBlocks)
    ranges = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        stripped = block.strip()
        lower = stripped.lower()

        if (stripped.startswith('** ABQ_Matching connector elements:') or
                stripped.startswith('** ABQ_Matching spring elements:')):
            start = i
            end = i
            while end < len(blocks):
                end_text = blocks[end].strip()
                if (end_text.startswith('** End ABQ_Matching connector elements:') or
                        end_text.startswith('** End ABQ_Matching spring elements:')):
                    break
                end += 1
            if end >= len(blocks):
                end = start
            ranges.append((start, end))
            i = end + 1
            continue

        if lower.startswith('*conflicts'):
            start = i
            end = i
            while end + 1 < len(blocks):
                next_text = blocks[end + 1].strip()
                if next_text.startswith('*') or next_text.startswith('**'):
                    break
                end += 1
            ranges.append((start, end))
            i = end + 1
            continue

        i += 1

    for start, end in reversed(ranges):
        _delete_keyword_block(model, start, end)

    if ranges:
        print('ABQ_Matching: removed %s old keyword/conflict block(s).' % len(ranges))


def _create_preview_wires(assembly, name, pairs, master_nodes, slave_nodes):
    points = []
    for master_index, slave_index, distance in pairs:
        points.append((master_nodes[master_index], slave_nodes[slave_index]))
    if not points:
        return
    assembly.WirePolyLine(points=tuple(points), mergeType=IMPRINT, meshable=OFF)
    try:
        edges = assembly.edges[-len(points):]
        assembly.Set(edges=edges, name=name + '-WireSet')
    except:
        pass


def connector_matching(modelName, setMaster, setSlave, serialNumber):
    model, assembly, master_nodes, slave_nodes = _get_model_and_sets(
        modelName, setMaster, setSlave)
    pairs = _match_nodes(master_nodes, slave_nodes)
    _cleanup_old_matching_keywords(model)

    base_name = _safe_name('Connector_matching', serialNumber)
    name = _unique_name(base_name, lambda candidate: candidate + '-WireSet' in assembly.sets.keys())

    _create_preview_wires(assembly, name, pairs, master_nodes, slave_nodes)

    _print_summary(name, pairs)
    assembly.regenerate()
