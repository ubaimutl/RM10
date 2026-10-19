#!/usr/bin/env python3
"""Model a saved lpdump; never connect to or modify a device.

Conservatively reserve extents from every stored metadata map, including COW
entries. Also calculate an optimistic active-map bound, without authorizing
reclamation of any extents. A successful capacity calculation is not a write
procedure or a recovery demonstration.
"""
import argparse
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from rm10_offline import PARTITIONS, sha256, write_json


def union(intervals):
    result = []
    for start, end in sorted(intervals):
        if start < 0 or end <= start:
            raise ValueError("invalid physical interval")
        if result and start <= result[-1][1]:
            result[-1] = result[-1][0], max(end, result[-1][1])
        else:
            result.append((start, end))
    return result


def overlap(a, b):
    return sum(max(0, min(x1, y1) - max(x0, y0))
               for x0, x1 in union(a) for y0, y1 in union(b))


def parse_layout(text):
    active = re.findall(r"^Current slot: _([ab])$", text, re.M)
    if not active or len(set(active)) != 1:
        raise ValueError("missing or inconsistent active-slot evidence")
    states = re.findall(r"^Update state: (\S+)$", text, re.M)
    if len(states) != 1:
        raise ValueError("missing or ambiguous snapshot update state")
    slots, capacities, first_sectors = {}, set(), set()
    for slot, block in re.findall(r"^Slot (\d+):\n(.*?)(?=^Slot \d+:|^---------------\nSnapshot state:|\Z)",
                                  text, re.M | re.S):
        if slot in slots:
            raise ValueError("duplicate metadata slot")
        sizes = re.findall(r"Partition name: super\n.*?Size: (\d+) bytes", block, re.S)
        if len(sizes) != 1:
            raise ValueError("expected a single super device per map")
        capacity = int(sizes[0]); capacities.add(capacity)
        starts = re.findall(r"Partition name: super\n\s+First sector: (\d+)", block)
        if len(starts) != 1:
            raise ValueError("missing first usable super sector")
        first_sector = int(starts[0]); first_sectors.add(first_sector)
        parts = {}
        table = block.split("Super partition layout:")[0]
        for name, data in re.findall(r"  Name: (\S+)\n(.*?)(?=------------------------)", table, re.S):
            if name in parts:
                raise ValueError("duplicate logical partition")
            if "Extents:" not in data:
                raise ValueError("missing extent table")
            lines = data.split("Extents:", 1)[1].strip().splitlines()
            extents, logical_end = [], 0
            for line in lines:
                m = re.fullmatch(r"\s*(\d+) \.\. (\d+) linear super (\d+)\s*", line)
                if not m:
                    raise ValueError("unsupported or empty extent: " + line)
                first, last, physical = map(int, m.groups())
                if first != logical_end or last < first:
                    raise ValueError("noncontiguous logical extent list")
                length = last - first + 1; logical_end += length
                start, end = physical * 512, (physical + length) * 512
                if end > capacity or start < first_sector * 512:
                    raise ValueError("extent exceeds usable super range")
                extents.append((start, end))
            if not extents:
                raise ValueError("empty partition cannot be modeled")
            if sum(b-a for a,b in extents) != sum(b-a for a,b in union(extents)):
                raise ValueError("a partition maps the same physical blocks twice")
            parts[name] = {"bytes": logical_end * 512, "intervals": extents}
        if not parts:
            raise ValueError("no logical partitions")
        all_intervals = [i for part in parts.values() for i in part["intervals"]]
        if sum(b-a for a,b in all_intervals) != sum(b-a for a,b in union(all_intervals)):
            raise ValueError("overlapping partitions within one metadata map")
        slots[slot] = parts
    if not {"0", "1"}.issubset(slots) or len(capacities) != 1 or len(first_sectors) != 1:
        raise ValueError("both A/B maps with consistent super capacity are required")
    return {"active": active[0], "snapshot_state": states[0],
            "super_bytes": capacities.pop(), "first_usable_byte": first_sectors.pop() * 512,
            "maps": slots}


def free_intervals(used, capacity, first_usable):
    # Reserve the beginning for geometry/metadata. No modeled write addresses
    # are produced; this is an upper bound on capacity, not an allocator.
    used = union([(0, first_usable)] + used)
    cursor, gaps = 0, []
    for start, end in used:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < capacity:
        gaps.append((cursor, capacity))
    return gaps


def model(layout, candidate, target, profile):
    candidate = Path(candidate)
    maps = layout["maps"]
    target_map = maps["0" if target == "a" else "1"]
    active_map = maps["0" if layout["active"] == "a" else "1"]
    active = [i for name, p in active_map.items() if name.endswith("_" + layout["active"])
              for i in p["intervals"]]
    if not active:
        raise ValueError("active logical map is empty")
    all_extents = [i for parts in maps.values() for p in parts.values() for i in p["intervals"]]
    changed = list(PARTITIONS) if profile == "full" else ["system"]
    rows = []
    for part in changed:
        name = part + "_" + target
        if name not in target_map:
            raise ValueError("target partition missing: " + name)
        p = target_map[name]
        image_size = (candidate / (part + ".img")).stat().st_size
        rows.append({"partition": part, "allocation_bytes": p["bytes"],
                     "image_bytes": image_size, "fits": image_size <= p["bytes"],
                     "footer_envelope_matches": image_size == p["bytes"],
                     "overlap_with_active_bytes": overlap(p["intervals"], active)})
    required = sum(r["image_bytes"] for r in rows)
    free_conservative = sum(b-a for a,b in free_intervals(all_extents, layout["super_bytes"], layout["first_usable_byte"]))
    free_optimistic = sum(b-a for a,b in free_intervals(active, layout["super_bytes"], layout["first_usable_byte"]))
    reasons = ["stock recovery and hardware acceptance are not established"]
    if target == layout["active"]:
        reasons.append("target is the active slot")
    if layout["snapshot_state"] != "none":
        reasons.append("snapshot update state is not none")
    if any(not r["fits"] for r in rows):
        reasons.append("one or more images exceed the target allocation")
    if any(not r["footer_envelope_matches"] for r in rows):
        reasons.append("image footer envelopes do not match current target capacities")
    if any(r["overlap_with_active_bytes"] for r in rows):
        reasons.append("proposed target writes overlap active physical extents")
    if required > free_conservative:
        reasons.append("no conservative disjoint allocation capacity for changed images")
    return {"schema": 1, "profile": profile, "observations_apply_only_to_supplied_layout": True,
            "active_slot": layout["active"], "target_slot": target,
            "snapshot_state": layout["snapshot_state"], "super_bytes": layout["super_bytes"],
            "images": rows, "changed_images_total_bytes": required,
            "free_preserving_all_recorded_maps_bytes": free_conservative,
            "free_preserving_only_active_map_upper_bound_bytes": free_optimistic,
            "disjoint_capacity_possible_under_optimistic_bound": required <= free_optimistic,
            "optimistic_bound_is_not_reclamation_authorization": True,
            "hardware_test_authorized": False, "blocking_reasons": reasons}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--layout", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--target-slot", required=True, choices=["a", "b"])
    p.add_argument("--profile", choices=["full", "system-only"], default="full")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--write-sizes", type=Path)
    args = p.parse_args()
    layout = parse_layout(args.layout.read_text())
    report = model(layout, args.candidate, args.target_slot, args.profile)
    report["layout_sha256"] = sha256(args.layout)
    for dst in [args.output, args.write_sizes]:
        if dst and dst.exists():
            raise ValueError("refusing to overwrite model output: " + str(dst))
    write_json(args.output, report)
    if args.write_sizes:
        target = layout["maps"]["0" if args.target_slot == "a" else "1"]
        write_json(args.write_sizes, {p: target[p + "_" + args.target_slot]["bytes"] for p in PARTITIONS})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        sys.exit(str(exc))
