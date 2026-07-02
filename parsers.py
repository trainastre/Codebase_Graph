import os
import ast
import re

def parse_python_file(filepath, base_dir, graph):
    rel_path = os.path.relpath(filepath, base_dir)
    graph.add_node(rel_path, group="file", id=rel_path, lang="python")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception:
        return True

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                graph.add_node(alias.name, group="module", id=alias.name, lang="python")
                graph.add_edge(rel_path, alias.name, type="imports")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                graph.add_node(node.module, group="module", id=node.module, lang="python")
                graph.add_edge(rel_path, node.module, type="imports")
        elif isinstance(node, ast.ClassDef):
            class_id = f"{rel_path}::{node.name}"
            graph.add_node(class_id, group="class", id=class_id, lang="python")
            graph.add_edge(rel_path, class_id, type="contains")
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    func_id = f"{class_id}::{item.name}"
                    graph.add_node(func_id, group="method", id=func_id, lang="python")
                    graph.add_edge(class_id, func_id, type="contains")
        elif isinstance(node, ast.FunctionDef):
            func_id = f"{rel_path}::{node.name}"
            graph.add_node(func_id, group="function", id=func_id, lang="python")
            graph.add_edge(rel_path, func_id, type="contains")
            
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
