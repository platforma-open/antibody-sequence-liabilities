import sys


# Base-36 Utilities
def base36_encode(n: int) -> str:
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0:
        return "0"
    s = ""
    while n > 0:
        n, r = divmod(n, 36)
        s = digits[r] + s
    return s


# Base-36 Decoding
def base36_decode(s: str) -> int:
    return int(s, 36)


# Parsing & Extraction
def parse_annotations(ann: str):
    segs = []
    if not ann or not isinstance(ann, str):
        return segs
    for part in ann.split("|"):
        if ":" not in part or "+" not in part:
            continue
        lab, rest = part.split(":", 1)
        st36, ln36 = rest.split("+", 1)
        try:
            segs.append((lab, base36_decode(st36), base36_decode(ln36)))
        except ValueError:
            print(f"Warning: Could not decode part '{part}' in annotation '{ann}'", file=sys.stderr)
            continue
    return sorted(segs, key=lambda x: x[1])


# Extract CDRs & FR1
def extract_cdrs_fr1(seq: str, segments: list, region_map: dict):
    frags, coords = {}, {}
    for lab, start, length in segments:
        name = region_map.get(str(lab))
        if name:
            if start < 0 or start + length > len(seq):
                print(
                    f"Warning: Segment {name} ({start}+{length}) out of bounds for seq length {len(seq)}.",
                    file=sys.stderr,
                )
                continue
            frags[name] = seq[start : start + length]
            coords[name] = (start, length)
    if "CDR1" in coords:
        s0, _ = coords["CDR1"]
        if s0 > 0:
            frags["FR1"] = seq[:s0]
            coords["FR1"] = (0, s0)
    return frags, coords
