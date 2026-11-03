import pathlib

b = pathlib.Path('index.html').read_bytes()
print('em-dash in source index.html:', '—'.encode() in b)
d = pathlib.Path('dist/index.html').read_bytes()
print('em-dash in dist/index.html:', '—'.encode() in d)
print('inline module script in dist:', b'<script type="module">' in d)
print('bootstrap referenced:', b'bootstrap.js' in d)
print('meta csp present:', b'Content-Security-Policy' in d)
