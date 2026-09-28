#!/usr/bin/env python3
"""On the VM: crop the object out of each library frame and write it as a small BMP.

The VM's python3 has no Pillow, so this reads and writes the 8-bit paletted BMP by hand.
Input   /tmp/ep_fiber_boxes.csv   (group, file_name, box_label, xtl, ytl, xbr, ybr, img_w, img_h)
Output  /tmp/epfiber_crops/<group>__<stem>.bmp   plus a manifest on stdout
"""
import csv
import hashlib
import os
import struct
import sys

ROOT = "/data/FMD_Data_26082026/fmd_temp_images/ICube Defects Library"
SEARCH = [
    os.path.join(ROOT, "Fiber"),
    os.path.join(ROOT, "Extraneous Polymer"),
]
OUT = "/tmp/epfiber_crops"
PAD = 0.35  # room to see the surroundings


def read_bmp(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] != b"BM":
        raise ValueError("not a BMP: " + path)
    off_bits = struct.unpack_from("<I", data, 10)[0]
    hdr = struct.unpack_from("<IiiHH", data, 14)
    width, height, planes, bpp = hdr[1], hdr[2], hdr[3], hdr[4]
    if bpp not in (8, 24):
        raise ValueError("unsupported bit depth %d in %s" % (bpp, path))
    return data, off_bits, width, abs(height), bpp, height < 0


def crop_pixels(path, x0, y0, x1, y1):
    data, off_bits, w, h, bpp, top_down = read_bmp(path)
    x0 = max(0, min(int(x0), w - 1)); x1 = max(x0 + 1, min(int(x1), w))
    y0 = max(0, min(int(y0), h - 1)); y1 = max(y0 + 1, min(int(y1), h))
    cw, ch = x1 - x0, y1 - y0
    if bpp == 8:
        palette = data[off_bits - 1024:off_bits]
        row_bytes = ((w + 3) // 4) * 4
        cw_row = ((cw + 3) // 4) * 4
        out = bytearray()
        for y in range(y0, y1):          # top down in the output
            src_y = y if top_down else (h - 1 - y)
            row = data[off_bits + src_y * row_bytes + x0: off_bits + src_y * row_bytes + x1]
            out += row + b"\x00" * (cw_row - cw)
        pixel_data = bytes(out)
        entry = 4
    else:
        palette = b""
        row_bytes = ((w * 3 + 3) // 4) * 4
        cw_row = ((cw * 3 + 3) // 4) * 4
        out = bytearray()
        for y in range(y0, y1):
            src_y = y if top_down else (h - 1 - y)
            row = data[off_bits + src_y * row_bytes + x0 * 3: off_bits + src_y * row_bytes + x1 * 3]
            out += row + b"\x00" * (cw_row - len(row))
        pixel_data = bytes(out)
        entry = 3
    # write a standard bottom-up BMP of the crop
    pixels = b"".join(pixel_data[i * cw_row: i * cw_row + cw_row] for i in range(ch - 1, -1, -1))
    off = 54 + len(palette)
    dib = struct.pack("<IiiHHIIiiII", 40, cw, ch, 1, bpp, 0, len(pixels), 2835, 2835, 0, 0)
    return b"BM" + struct.pack("<IHHI", off + len(pixels), 0, 0, off) + dib + palette + pixels


def find(name):
    for d in SEARCH:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(open("/tmp/ep_fiber_boxes.csv", newline="", encoding="utf-8")))
    print("group,file_name,md5,file_bytes,src_w,src_h,src_bpp,crop_w,crop_h")
    missing = 0
    for r in rows:
        path = find(r["file_name"])
        if not path:
            print("MISSING,,,,,,,,%s" % r["file_name"])
            missing += 1
            continue
        raw = open(path, "rb").read()
        md5 = hashlib.md5(raw).hexdigest()
        _, _, w, h, bpp, _ = read_bmp(path)
        x0, y0 = float(r["xtl"]), float(r["ytl"])
        x1, y1 = float(r["xbr"]), float(r["ybr"])
        pw = PAD * max(x1 - x0, y1 - y0)
        out = crop_pixels(path, x0 - pw, y0 - pw, x1 + pw, y1 + pw)
        stem = r["file_name"].rsplit(".", 1)[0]
        dst = os.path.join(OUT, "%s__%s_%s.bmp" % (r["group"], r["box_idx"], stem))
        open(dst, "wb").write(out)
        cw = struct.unpack_from("<i", out, 18)[0]
        ch = struct.unpack_from("<i", out, 22)[0]
        print("%s,%s,%s,%d,%d,%d,%d,%d,%d"
              % (r["group"], r["file_name"], md5, len(raw), w, h, bpp, cw, ch))
    print("missing files: %d of %d" % (missing, len(rows)), file=sys.stderr)


main()
