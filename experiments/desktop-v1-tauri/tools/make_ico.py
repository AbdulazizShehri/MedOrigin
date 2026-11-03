import pathlib
import struct

icons_dir = pathlib.Path(__file__).resolve().parent.parent / 'src-tauri' / 'icons'

# Build a PNG-compressed .ico from the generated placeholder PNGs.
source = icons_dir / 'icon.png'  # 512x512 placeholder
images = [(icons_dir / n, s) for n, s in [('32x32.png', 32), ('128x128.png', 128), ('128x128@2x.png', 256)]]

entries = []
blob = b''
offset = 6 + 16 * len(images)
for path, size in images:
    data = path.read_bytes()
    entries.append((size, data, offset))
    blob += data
    offset += len(data)

ico = struct.pack('<HHH', 0, 1, len(entries))
for size, data, off in entries:
    w = 0 if size >= 256 else size
    ico += struct.pack('<BBBBHHII', w, w, 0, 0, 1, 32, len(data), off)
ico += blob
out = icons_dir / 'icon.ico'
out.write_bytes(ico)
print('wrote', out, len(ico), 'bytes with', len(entries), 'sizes')
