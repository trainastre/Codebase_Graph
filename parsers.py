import os
import ast
import re

class PythonCodeVisitor(ast.NodeVisitor):
    def __init__(self, rel_path, graph):
        self.rel_path = rel_path
        self.graph = graph
        self.current_scope = [rel_path]

    def visit_Import(self, node):
        for alias in node.names:
            self.graph.add_node(alias.name, group="module", id=alias.name, lang="python")
            self.graph.add_edge(self.rel_path, alias.name, type="imports")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.graph.add_node(node.module, group="module", id=node.module, lang="python")
            self.graph.add_edge(self.rel_path, node.module, type="imports")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_id = f"{self.rel_path}::{node.name}"
        self.graph.add_node(class_id, group="class", id=class_id, lang="python")
        self.graph.add_edge(self.current_scope[-1], class_id, type="contains")
        
        for base in node.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name:
                self.graph.add_node(base_name, group="class", id=base_name, lang="python")
                self.graph.add_edge(class_id, base_name, type="extends")

        self.current_scope.append(class_id)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node):
        func_id = f"{self.current_scope[-1]}::{node.name}"
        group = "method" if "::" in self.current_scope[-1] else "function"
        self.graph.add_node(func_id, group=group, id=func_id, lang="python")
        self.graph.add_edge(self.current_scope[-1], func_id, type="contains")
        
        self.current_scope.append(func_id)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_Call(self, node):
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            
        if func_name:
            self.graph.add_node(func_name, group="function", id=func_name, lang="python")
            self.graph.add_edge(self.current_scope[-1], func_name, type="calls")
            
        self.generic_visit(node)

def parse_python_file(filepath, base_dir, graph):
    rel_path = os.path.relpath(filepath, base_dir)
    graph.add_node(rel_path, group="file", id=rel_path, lang="python")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception:
        return True

    visitor = PythonCodeVisitor(rel_path, graph)
    visitor.visit(tree)
            
    return True

def parse_js_ts_file(filepath, base_dir, graph):
    rel_path = os.path.relpath(filepath, base_dir)
    ext = os.path.splitext(filepath)[1].lower()
    lang = "typescript" if ext in ('.ts', '.tsx') else "javascript"
    graph.add_node(rel_path, group="file", id=rel_path, lang=lang)
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return True

    import_re = re.compile(r'(?:import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))')
    for match in import_re.finditer(content):
        module = match.group(1) or match.group(2)
        if module:
            graph.add_node(module, group="module", id=module, lang=lang)
            graph.add_edge(rel_path, module, type="imports")
            
    class_re = re.compile(r'class\s+([A-Za-z0-9_]+)')
    for match in class_re.finditer(content):
        class_name = match.group(1)
        class_id = f"{rel_path}::{class_name}"
        graph.add_node(class_id, group="class", id=class_id, lang=lang)
        graph.add_edge(rel_path, class_id, type="contains")
        
    func_re = re.compile(r'(?:function\s+([A-Za-z0-9_]+)\s*\(|const\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)\s*=>|function\s*\())')
    for match in func_re.finditer(content):
        func_name = match.group(1) or match.group(2)
        if func_name:
            func_id = f"{rel_path}::{func_name}"
            graph.add_node(func_id, group="function", id=func_id, lang=lang)
            graph.add_edge(rel_path, func_id, type="contains")
            
    return True

def parse_java_file(filepath, base_dir, graph):
    rel_path = os.path.relpath(filepath, base_dir)
    graph.add_node(rel_path, group="file", id=rel_path, lang="java")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return True

    import_re = re.compile(r'import\s+([\w\.]+);')
    for match in import_re.finditer(content):
        module = match.group(1)
        graph.add_node(module, group="module", id=module, lang="java")
        graph.add_edge(rel_path, module, type="imports")
        
    class_re = re.compile(r'(?:class|interface|enum)\s+([A-Za-z0-9_]+)')
    for match in class_re.finditer(content):
        class_name = match.group(1)
        class_id = f"{rel_path}::{class_name}"
        graph.add_node(class_id, group="class", id=class_id, lang="java")
        graph.add_edge(rel_path, class_id, type="contains")
        
    method_re = re.compile(r'(?:public|protected|private|static|\s) +[\w\<\>\[\]]+\s+([A-Za-z0-9_]+)\s*\(')
    for match in method_re.finditer(content):
        method_name = match.group(1)
        if method_name not in ('if', 'for', 'while', 'switch', 'catch'):
            method_id = f"{rel_path}::{method_name}"
            graph.add_node(method_id, group="method", id=method_id, lang="java")
            graph.add_edge(rel_path, method_id, type="contains")
            
    return True

def parse_file(filepath, base_dir, graph):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.py':
        return parse_python_file(filepath, base_dir, graph)
    elif ext in ('.js', '.ts', '.jsx', '.tsx'):
        return parse_js_ts_file(filepath, base_dir, graph)
    elif ext == '.java':
        return parse_java_file(filepath, base_dir, graph)
    
    return False
