import re

class JSAnalyzer:
    def __init__(self):
        # Patterns for: 
        # function foo()
        # const foo = () =>
        # export function foo()
        # class Foo
        self.func_pattern = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(')
        self.arrow_pattern = re.compile(r'(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(.*?\)\s*=>')
        self.class_pattern = re.compile(r'(?:export\s+)?class\s+([a-zA-Z0-9_$]+)')
        
        # New patterns
        self.export_pattern = re.compile(r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+([a-zA-Z0-9_$]+)')
        self.fetch_pattern = re.compile(r'fetch\s*\(\s*["\']([^"\']+)["\']')
        self.axios_pattern = re.compile(r'axios\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')

    def analyze(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            functions = []
            classes = []
            exports = []
            api_routes = []
            
            functions.extend(self.func_pattern.findall(content))
            functions.extend(self.arrow_pattern.findall(content))
            classes.extend(self.class_pattern.findall(content))
            
            exports.extend(self.export_pattern.findall(content))
            api_routes.extend(self.fetch_pattern.findall(content))
            api_routes.extend(self.axios_pattern.findall(content))
            
            return {
                "functions": list(set(functions)),
                "classes": list(set(classes)),
                "exports": list(set(exports)),
                "api_routes": list(set(api_routes)),
                "type": "javascript"
            }
        except Exception as e:
            return {"error": str(e), "type": "javascript"}
