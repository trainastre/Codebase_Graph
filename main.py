import os
import ast
import tempfile
import subprocess
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import networkx as nx

app = FastAPI()

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
  <title>Codebase Graph</title>
  <style>
    body { margin: 0; overflow: hidden; font-family: sans-serif; background-color: #000011; }
    #ui { position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(255,255,255,0.9); padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    input { padding: 8px; width: 300px; border: 1px solid #ccc; border-radius: 4px; }
    button { padding: 8px 15px; background-color: #0366d6; color: white; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background-color: #005cc5; }
    #loading { display: none; margin-top: 10px; color: #666; font-size: 14px; }
    .legend { margin-top: 15px; font-size: 12px; }
    .legend-item { display: flex; align-items: center; margin-bottom: 5px; }
    .color-box { width: 12px; height: 12px; margin-right: 8px; border-radius: 2px; }
  </style>
  <script src="https://unpkg.com/3d-force-graph"></script>
</head>
<body>
  <div id="ui">
    <h3 style="margin-top: 0;">Codebase Graph</h3>
    <input type="text" id="repoUrl" placeholder="https://github.com/owner/repo" value="https://github.com/trainastre/Codebase_Graph" />
    <button onclick="loadGraph()">Visualize</button>
    <div id="loading">Cloning and parsing repository...</div>
    
    <div class="legend">
      <div class="legend-item"><div class="color-box" style="background: #ff5722;"></div> File</div>
      <div class="legend-item"><div class="color-box" style="background: #4caf50;"></div> Class</div>
      <div class="legend-item"><div class="color-box" style="background: #2196f3;"></div> Function/Method</div>
      <div class="legend-item"><div class="color-box" style="background: #9c27b0;"></div> External Module</div>
    </div>
  </div>
  <div id="3d-graph"></div>

  <script>
    const colorMap = {
      'file': '#ff5722',
      'class': '#4caf50',
      'function': '#2196f3',
      'method': '#2196f3',
      'module': '#9c27b0',
      'unknown': '#999999'
    };

    const Graph = ForceGraph3D()
      (document.getElementById('3d-graph'))
        .nodeColor(node => colorMap[node.group] || colorMap['unknown'])
        .nodeLabel('id')
        .linkDirectionalArrowLength(3.5)
        .linkDirectionalArrowRelPos(1)
        .linkCurvature(0.1)
        .linkOpacity(0.3);

    async function loadGraph() {
      const repoUrl = document.getElementById('repoUrl').value;
      if (!repoUrl) return;
      
      document.getElementById('loading').style.display = 'block';
      try {
        const response = await fetch(`/api/graph?repo_url=${encodeURIComponent(repoUrl)}`);
        if (!response.ok) {
          throw new Error(await response.text());
        }
        const data = await response.json();
        Graph.graphData(data);
      } catch (err) {
        alert('Error: ' + err.message);
      } finally {
        document.getElementById('loading').style.display = 'none';
      }
    }
    
    // Load default graph on start
    loadGraph();
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_CONTENT

def parse_python_file(filepath, base_dir, graph):
    rel_path = os.path.relpath(filepath, base_dir)
    graph.add_node(rel_path, group="file", id=rel_path)
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception:
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                graph.add_node(alias.name, group="module", id=alias.name)
                graph.add_edge(rel_path, alias.name, type="imports")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                graph.add_node(node.module, group="module", id=node.module)
                graph.add_edge(rel_path, node.module, type="imports")
        elif isinstance(node, ast.ClassDef):
            class_id = f"{rel_path}::{node.name}"
            graph.add_node(class_id, group="class", id=class_id)
            graph.add_edge(rel_path, class_id, type="contains")
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    func_id = f"{class_id}::{item.name}"
                    graph.add_node(func_id, group="method", id=func_id)
                    graph.add_edge(class_id, func_id, type="contains")
        elif isinstance(node, ast.FunctionDef):
            # Top level function
            func_id = f"{rel_path}::{node.name}"
            graph.add_node(func_id, group="function", id=func_id)
            graph.add_edge(rel_path, func_id, type="contains")

@app.get("/api/graph")
async def get_graph(repo_url: str):
    if not repo_url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Only GitHub URLs are supported")
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone the repository
        subprocess.run(["git", "clone", "--depth", "1", repo_url, temp_dir], check=True, capture_output=True)
        
        graph = nx.DiGraph()
        
        # Walk the directory and parse Python files
        for root, _, files in os.walk(temp_dir):
            # Skip hidden directories like .git
            if "/." in root or "\\." in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    parse_python_file(filepath, temp_dir, graph)
                    
        # Convert to 3d-force-graph format
        nodes = [{"id": n, "group": d.get("group", "unknown")} for n, d in graph.nodes(data=True)]
        links = [{"source": u, "target": v, "type": d.get("type", "")} for u, v, d in graph.edges(data=True)]
        
        return {"nodes": nodes, "links": links}
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e.stderr.decode() if e.stderr else str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
