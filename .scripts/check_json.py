import os
import json

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
errors = []
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        if fn.lower().endswith('.json'):
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                errors.append((path, str(e), e.lineno, e.colno, e.pos))
            except Exception as e:
                errors.append((path, repr(e), None, None, None))

if not errors:
    print('OK: no JSON errors found')
else:
    print(f'FOUND {len(errors)} JSON error(s):')
    for p, msg, ln, col, pos in errors:
        print('---')
        print(f'File: {p}')
        print(f'Error: {msg}')
        if ln is not None:
            print(f'Line: {ln}  Column: {col}  Pos: {pos}')
        # show surrounding text when possible
        try:
            with open(p, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            if pos is not None and isinstance(pos, int):
                start = max(0, pos-40)
                end = min(len(text), pos+40)
                snippet = text[start:end]
                print('Context snippet:')
                print(snippet)
        except Exception:
            pass

# exit code
if errors:
    raise SystemExit(1)
