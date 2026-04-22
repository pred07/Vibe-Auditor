import ast

class PythonAnalyzer:
    def __init__(self):
        pass

    def analyze(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            try:
                tree = ast.parse(content)
            except SyntaxError as se:
                return {
                    "type": "python",
                    "error": f"Syntax Error: {se.msg} at line {se.lineno}",
                    "has_syntax_error": True,
                    "syntax_error_details": {
                        "msg": se.msg,
                        "lineno": se.lineno,
                        "offset": se.offset,
                        "text": se.text
                    }
                }

            functions = []
            classes = []
            imports = []
            try_except_count = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if it's a top-level function or a method (this walk is flat, so we need to be careful)
                    # For simplicity in this AST walk, we'll collect all functions
                    # But we can check if the parent is a ClassDef later or during a better traversal
                    args = [arg.arg for arg in node.args.args]
                    functions.append({
                        "name": node.name,
                        "args": args,
                        "lineno": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "decorators": [ast.dump(d) for d in node.decorator_list]
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            m_args = [arg.arg for arg in item.args.args]
                            methods.append({
                                "name": item.name,
                                "args": m_args,
                                "lineno": item.lineno
                            })
                    classes.append({
                        "name": node.name,
                        "lineno": node.lineno,
                        "methods": methods
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:
                        imports.append(node.module)
                elif isinstance(node, ast.Try):
                    try_except_count += 1
            
            # De-duplicate imports
            imports = list(set(filter(None, imports)))
            
            return {
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "try_except_count": try_except_count,
                "type": "python",
                "has_syntax_error": False
            }
        except Exception as e:
            return {"error": str(e), "type": "python"}
