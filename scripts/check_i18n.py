#!/usr/bin/env python3
"""
Check that all i18n language files expose the same API.
Run: python3 scripts/check_i18n.py

Uses AST parsing to avoid import dependencies.
"""
import sys
import os
import ast

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_msg_api_from_ast(filepath):
    """Parse MSG class from file without importing."""
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    api = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'MSG':
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Get method parameters
                    args = [a.arg for a in item.args.args if a.arg != 'self']
                    api[item.name] = ('method', f"({', '.join(args)})")
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            # Determine type from value
                            if isinstance(item.value, ast.Constant):
                                vtype = type(item.value.value).__name__
                            elif isinstance(item.value, ast.Dict):
                                vtype = 'dict'
                            elif isinstance(item.value, ast.Tuple):
                                vtype = 'tuple'
                            elif isinstance(item.value, ast.JoinedStr):
                                vtype = 'str'
                            else:
                                vtype = 'unknown'
                            api[target.id] = ('const', vtype)
    return api

def main():
    print("Checking i18n API compatibility...")
    print("=" * 50)

    i18n_dir = os.path.join(PROJECT_ROOT, 'app', 'i18n')
    apis = {}

    for lang in ['en', 'ru', 'hy']:
        filepath = os.path.join(i18n_dir, f'{lang}.py')
        if not os.path.exists(filepath):
            print(f"FAIL: {filepath} not found")
            sys.exit(1)

        try:
            api = get_msg_api_from_ast(filepath)
            apis[lang] = api
            print(f"{lang}: {len(api)} members")
        except Exception as e:
            print(f"FAIL: Could not parse {lang}.py: {e}")
            sys.exit(1)

    print()

    # Use English as reference
    ref = apis['en']
    errors = []

    for lang in ['ru', 'hy']:
        other = apis[lang]

        # Check for missing members
        missing = set(ref.keys()) - set(other.keys())
        if missing:
            errors.append(f"{lang}: Missing members: {sorted(missing)}")

        # Check for extra members
        extra = set(other.keys()) - set(ref.keys())
        if extra:
            errors.append(f"{lang}: Extra members: {sorted(extra)}")

        # Check for type mismatches (method vs const)
        for name in set(ref.keys()) & set(other.keys()):
            ref_type = ref[name][0]
            other_type = other[name][0]
            if ref_type != other_type:
                errors.append(f"{lang}.{name}: type mismatch - expected {ref_type}, got {other_type}")

    if errors:
        print("ERRORS FOUND:")
        for err in errors:
            print(f"  - {err}")
        print()
        print("FAIL: API mismatch detected")
        sys.exit(1)

    print("All languages have matching API!")
    print()

    # Show the API
    print("MSG class API:")
    for name, (kind, sig) in sorted(ref.items()):
        if kind == 'method':
            print(f"  {name}{sig}")
        else:
            print(f"  {name} ({sig})")

    print()
    print("PASS: All i18n files are compatible")
    return 0

if __name__ == '__main__':
    sys.exit(main())
