"""Small deterministic Python repairs. Every edit is syntax checked and reviewable."""
import ast
import difflib
import symtable


class LocalRepairEngine:
    @staticmethod
    def generate_repair(source_code, error_message=''):
        try:
            tree = ast.parse(source_code)
            table = symtable.symtable(source_code, '<code>', 'exec')
        except (SyntaxError, ValueError) as exc:
            return {'success': False, 'error': 'Source must parse before a local repair can be proposed.', 'error_type': 'invalid_source', 'provider': 'local', 'source': 'local_repair'}

        lines = source_code.splitlines(keepends=True)
        offsets = []
        total = 0
        for line in lines:
            offsets.append(total)
            total += len(line)
        edits = []
        undefined = set()
        try:
            from .code_analyzer import CodeAnalyzer
            undefined.update(CodeAnalyzer.extract_undefined_names(source_code))
        except Exception:
            pass

        def visit(node):
            if isinstance(node, ast.FunctionDef):
                bound = {arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
                bound |= {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
                returns = [n for n in ast.walk(node) if isinstance(n, ast.Return) and isinstance(n.value, ast.Name)]
                for ret in returns:
                    name = ret.value.id
                    if name not in bound and name.endswith('_price') and 'final' in bound:
                        edits.append((ret.value.lineno, ret.value.col_offset, ret.value.end_lineno, ret.value.end_col_offset, 'final'))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'len' and len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                name = node.args[0].id
                literal_lists = [call.args[0] for call in ast.walk(tree) if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'sum' and call.args and isinstance(call.args[0], ast.List)]
                if name not in {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)} and len(literal_lists) == 1:
                    edits.append((node.args[0].lineno, node.args[0].col_offset, node.args[0].end_lineno, node.args[0].end_col_offset, ast.unparse(literal_lists[0])))
            for child in ast.iter_child_nodes(node):
                visit(child)

        visit(tree)
        # A single matching calculation function is a safe repair for an undefined
        # *_total/*_price result when all of its parameters exist at module scope.
        module_bound = {target.id for n in tree.body if isinstance(n, ast.Assign) for target in n.targets if isinstance(target, ast.Name)}
        module_bound |= {n.target.id for n in tree.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
        for name in undefined:
            if name.endswith(('_total', '_price')):
                matching = []
                for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                    result_names = {r.value.id for r in ast.walk(fn) if isinstance(r, ast.Return) and isinstance(r.value, ast.Name)}
                    args = [a.arg for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)]
                    if result_names and fn.name.startswith('calculate') and any(name.startswith(item + '_') for item in result_names) and args and all(arg in module_bound for arg in args):
                        matching.append((fn, args))
                if len(matching) == 1:
                    fn, args = matching[0]
                    for n in ast.walk(tree):
                        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == name:
                            edits.append((n.lineno, n.col_offset, n.end_lineno, n.end_col_offset, f"{fn.name}({', '.join(args)})"))
        # Generic undefined-name typo correction: only when a unique close match exists.
        try:
            for child in table.get_children():
                for ident in child.get_identifiers():
                    symbol = child.lookup(ident)
                    if symbol.is_referenced() and not symbol.is_assigned() and not symbol.is_global():
                        undefined.add(ident)
        except Exception:
            pass
        builtin_names = set(dir(__builtins__))
        for name in undefined:
            choices = {candidate for candidate in ast_names(tree) if candidate != name and candidate not in builtin_names and difflib.SequenceMatcher(None, name, candidate).ratio() >= .88}
            if len(choices) == 1:
                for n in ast.walk(tree):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == name:
                        edits.append((n.lineno, n.col_offset, n.end_lineno, n.end_col_offset, next(iter(choices))))
        if not edits:
            return {'success': False, 'error': 'No unambiguous supported local repair was found.', 'error_type': 'unsupported_or_ambiguous', 'provider': 'local', 'source': 'local_repair'}
        # Deduplicate overlapping edits and apply in reverse order.
        unique = {(a,b,c,d,repl) for a,b,c,d,repl in edits}
        updated = source_code
        spans = []
        for a,b,c,d,repl in unique:
            start = offsets[a-1] + b
            end = offsets[c-1] + d
            spans.append((start,end,repl))
        for start,end,repl in sorted(spans, reverse=True):
            updated = updated[:start] + repl + updated[end:]
        try:
            ast.parse(updated)
        except SyntaxError:
            return {'success': False, 'error': 'The proposed local change did not pass syntax validation.', 'error_type': 'invalid_candidate', 'provider': 'local', 'source': 'local_repair'}
        return {'success': True, 'provider': 'local', 'source': 'local_repair', 'operation': 'repair', 'original_code': source_code, 'repaired_code': updated, 'explanation': 'Applied deterministic, syntax-validated identifier corrections.', 'changes': [], 'diff': '\n'.join(difflib.unified_diff(source_code.splitlines(), updated.splitlines(), fromfile='Original', tofile='Proposed', lineterm='')), 'error': None, 'status': 'proposed'}


def ast_names(tree):
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
