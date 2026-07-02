import os
import tempfile
import subprocess
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import networkx as nx

from parsers import parse_file

app = FastAPI()

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
  <title>Codebase Graph</title>
  <style>
    body { margin: 0; overflow: hidden; font-family: sans-serif; background-color: #000011; color: white; }
    #ui { position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(30,30,30,0.9); padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); max-height: 90vh; overflow-y: auto; }
    input[type="text"] { padding: 8px; width: 300px; border: 1px solid #555; border-radius: 4px; background: #222; color: white; }
    button { padding: 8px 15px; background-color: #0366d6; color: white; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background-color: #005cc5; }
    #loading { display: none; margin-top: 10px; color: #aaa; font-size: 14px; }
    .legend { margin-top: 15px; font-size: 12px; }
    .legend-item { display: flex; align-items: center; margin-bottom: 5px; }
    .color-box { width: 12px; height: 12px; margin-right: 8px; border-radius: 2px; }
    #filters { margin-top: 15px; font-size: 13px; display: flex; flex-direction: column; gap: 5px; }
  </style>
  <script src="https://unpkg.com/3d-force-graph"></script>
</head>
<body>
  <div id="ui">
    <h3 style="margin-top: 0;">Codebase Graph</h3>
    <input type="text" id="repoUrl" placeholder="https://github.com/owner/repo" value="https://github.com/trainastre/Codebase_Graph" />
    <button onclick="loadGraph()">Visualize</button>
    <div id="loading">Cloning and parsing repository...</div>
    
    <div id="filters">
      <strong>Nodes:</strong>
      <label><input type="checkbox" id="showFolders" checked onchange="applyFilters()"> Folders</label>
      <label><input type="checkbox" id="showFiles" checked onchange="applyFilters()"> Files</label>
      <label><input type="checkbox" id="showClasses" checked onchange="applyFilters()"> Classes</label>
      <label><input type="checkbox" id="showMethods" checked onchange="applyFilters()"> Methods/Functions</label>
      <label><input type="checkbox" id="showModules" checked onchange="applyFilters()"> External Modules</label>
      <hr style="margin: 5px 0; border-color: #444;">
      <strong>Relationships:</strong>
      <label><input type="checkbox" id="showContains" checked onchange="applyFilters()"> Contains</label>
      <label><input type="checkbox" id="showImports" checked onchange="applyFilters()"> Imports</label>
      <label><input type="checkbox" id="showCalls" checked onchange="applyFilters()"> Calls</label>
      <label><input type="checkbox" id="showExtends" checked onchange="applyFilters()"> Extends</label>
    </div>

    <div class="legend">
      <div class="legend-item"><div class="color-box" style="background: #ffc107;"></div> Folder</div>
      <div class="legend-item"><div class="color-box" style="background: #ff5722;"></div> File</div>
      <div class="legend-item"><div class="color-box" style="background: #4caf50;"></div> Class</div>
      <div class="legend-item"><div class="color-box" style="background: #2196f3;"></div> Function/Method</div>
      <div class="legend-item"><div class="color-box" style="background: #9c27b0;"></div> External Module</div>
      <hr style="margin: 5px 0; border-color: #444;">
      <div class="legend-item"><div class="color-box" style="background: rgba(255,255,255,0.4);"></div> Contains</div>
      <div class="legend-item"><div class="color-box" style="background: rgba(156,39,176,0.8);"></div> Imports</div>
      <div class="legend-item"><div class="color-box" style="background: rgba(33,150,243,0.8);"></div> Calls</div>
      <div class="legend-item"><div class="color-box" style="background: rgba(76,175,80,0.8);"></div> Extends</div>
      <div class="legend-item"><div class="color-box" style="background: red;"></div> Circular Dependency</div>
    </div>
  </div>
  <div id="3d-graph"></div>

  <script>
    const colorMap = {
      'folder': '#ffc107',
      'file': '#ff5722',
      'class': '#4caf50',
      'function': '#2196f3',
      'method': '#2196f3',
      'module': '#9c27b0',
      'unknown': '#999999'
    };

    const linkColorMap = {
      'contains': 'rgba(255,255,255,0.4)',
      'imports': 'rgba(156,39,176,0.8)',
      'calls': 'rgba(33,150,243,0.8)',
      'extends': 'rgba(76,175,80,0.8)'
    };

    const highlightNodes = new Set();
    const highlightLinks = new Set();
    let hoverNode = null;

    const Graph = ForceGraph3D()
      (document.getElementById('3d-graph'))
        .nodeColor(node => {
          if (highlightNodes.has(node)) {
            return node === hoverNode ? 'rgb(255,0,0,1)' : 'rgba(255,160,0,0.8)';
          }
          return colorMap[node.group] || colorMap['unknown'];
        })
        .linkWidth(link => highlightLinks.has(link) ? 2 : 1)
        .linkDirectionalParticles(link => highlightLinks.has(link) ? 4 : 0)
        .linkDirectionalParticleWidth(4)
        .nodeLabel('id')
        .linkColor(link => link.circular ? 'red' : (linkColorMap[link.type] || 'rgba(255,255,255,0.4)'))
        .linkDirectionalArrowLength(3.5)
        .linkDirectionalArrowRelPos(1)
        .linkCurvature(0.1)
        .linkOpacity(0.5)
        .onNodeHover(node => {
          if ((!node && !highlightNodes.size) || (node && hoverNode === node)) return;

          highlightNodes.clear();
          highlightLinks.clear();
          if (node) {
            highlightNodes.add(node);
            const { links } = Graph.graphData();
            links.forEach(link => {
              if (link.source.id === node.id || link.target.id === node.id) {
                highlightLinks.add(link);
                highlightNodes.add(link.source);
                highlightNodes.add(link.target);
              }
            });
          }

          hoverNode = node || null;
          updateHighlight();
        })
        .onNodeClick(node => {
          // Aim at node from outside it
          const distance = 100;
          const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);

          Graph.cameraPosition(
            { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // new position
            node, // lookAt ({ x, y, z })
            2000  // ms transition duration
          );
        });

    function updateHighlight() {
      // trigger update of highlighted objects in scene
      Graph
        .nodeColor(Graph.nodeColor())
        .linkWidth(Graph.linkWidth())
        .linkDirectionalParticles(Graph.linkDirectionalParticles());
    }

    let fullData = { nodes: [], links: [] };

    async function loadGraph() {
      const repoUrl = document.getElementById('repoUrl').value;
      if (!repoUrl) return;
      
      document.getElementById('loading').style.display = 'block';
      try {
        const response = await fetch(`/api/graph?repo_url=${encodeURIComponent(repoUrl)}`);
        if (!response.ok) {
          throw new Error(await response.text());
        }
        fullData = await response.json();
        applyFilters();
      } catch (err) {
        alert('Error: ' + err.message);
      } finally {
        document.getElementById('loading').style.display = 'none';
      }
    }
    
    function applyFilters() {
      if (!fullData.nodes.length) return;
      
      const showFolders = document.getElementById('showFolders').checked;
      const showFiles = document.getElementById('showFiles').checked;
      const showClasses = document.getElementById('showClasses').checked;
      const showMethods = document.getElementById('showMethods').checked;
      const showModules = document.getElementById('showModules').checked;

      const showContains = document.getElementById('showContains').checked;
      const showImports = document.getElementById('showImports').checked;
      const showCalls = document.getElementById('showCalls').checked;
      const showExtends = document.getElementById('showExtends').checked;

      const allowedGroups = new Set();
      if (showFolders) allowedGroups.add('folder');
      if (showFiles) allowedGroups.add('file');
      if (showClasses) allowedGroups.add('class');
      if (showMethods) {
        allowedGroups.add('method');
        allowedGroups.add('function');
      }
      if (showModules) allowedGroups.add('module');
      allowedGroups.add('unknown');

      const allowedLinkTypes = new Set();
      if (showContains) allowedLinkTypes.add('contains');
      if (showImports) allowedLinkTypes.add('imports');
      if (showCalls) allowedLinkTypes.add('calls');
      if (showExtends) allowedLinkTypes.add('extends');

      const filteredNodes = fullData.nodes.filter(n => allowedGroups.has(n.group));
      const nodeIds = new Set(filteredNodes.map(n => n.id));
      
      const parentMap = {};
      fullData.links.forEach(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        if (l.type === 'contains') {
          parentMap[targetId] = sourceId;
        }
      });

      function getVisibleAncestor(nodeId) {
        let current = parentMap[nodeId];
        while (current && !nodeIds.has(current)) {
          current = parentMap[current];
        }
        return current;
      }

      const filteredLinks = [];
      fullData.links.forEach(l => {
        if (!allowedLinkTypes.has(l.type)) return;

        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        
        if (nodeIds.has(sourceId) && nodeIds.has(targetId)) {
          filteredLinks.push(l);
        } else if (nodeIds.has(targetId) && !nodeIds.has(sourceId) && l.type === 'contains') {
          const visibleAncestor = getVisibleAncestor(targetId);
          if (visibleAncestor) {
            filteredLinks.push({ source: visibleAncestor, target: targetId, type: 'contains', circular: l.circular });
          }
        }
      });

      Graph.graphData({ nodes: filteredNodes, links: filteredLinks });
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

class CodeVisitor(ast.NodeVisitor):
    def __init__(self, rel_path, graph):
        self.rel_path = rel_path
        self.graph = graph
        self.current_scope = [rel_path]

    def visit_Import(self, node):
        for alias in node.names:
            self.graph.add_node(alias.name, group="module", id=alias.name)
            self.graph.add_edge(self.rel_path, alias.name, type="imports")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.graph.add_node(node.module, group="module", id=node.module)
            self.graph.add_edge(self.rel_path, node.module, type="imports")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_id = f"{self.current_scope[-1]}::{node.name}"
        self.graph.add_node(class_id, group="class", id=class_id)
        self.graph.add_edge(self.current_scope[-1], class_id, type="contains")
        
        for base in node.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name:
                self.graph.add_node(base_name, group="class", id=base_name)
                self.graph.add_edge(class_id, base_name, type="extends")

        self.current_scope.append(class_id)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node):
        func_id = f"{self.current_scope[-1]}::{node.name}"
        group = "method" if "::" in self.current_scope[-1] else "function"
        self.graph.add_node(func_id, group=group, id=func_id)
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
            self.graph.add_node(func_name, group="function", id=func_name)
            self.graph.add_edge(self.current_scope[-1], func_name, type="calls")
            
        self.generic_visit(node)

def parse_python_file(filepath, base_dir, graph):
    rel_path = os.path.relpath(filepath, base_dir)
    graph.add_node(rel_path, group="file", id=rel_path)
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception:
        return

    visitor = CodeVisitor(rel_path, graph)
    visitor.visit(tree)

@app.get("/api/graph")
async def get_graph(repo_url: str):
    if not repo_url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Only GitHub URLs are supported")
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone the repository
        subprocess.run(["git", "clone", "--depth", "1", repo_url, temp_dir], check=True, capture_output=True)
        
        graph = nx.DiGraph()
        
        # Walk the directory and parse files
        for root, dirs, files in os.walk(temp_dir):
            # Skip hidden directories like .git
            if "/." in root or "\\." in root or os.path.basename(root).startswith("."):
                continue
                
            rel_root = os.path.relpath(root, temp_dir)
            if rel_root != ".":
                graph.add_node(rel_root, group="folder", id=rel_root)
                parent = os.path.dirname(rel_root)
                if parent and parent != "":
                    graph.add_edge(parent, rel_root, type="contains")
                
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, temp_dir)
                
                if parse_file(filepath, temp_dir, graph):
                    if rel_root != ".":
                        graph.add_edge(rel_root, rel_path, type="contains")
                    
        # Detect circular dependencies
        for node in list(graph.nodes()):
            try:
                cycle_edges = nx.find_cycle(graph, source=node, orientation="directed")
                for u, v, _ in cycle_edges:
                    if graph.has_edge(u, v):
                        graph[u][v]['circular'] = True
            except nx.NetworkXNoCycle:
                continue
                    
        # Convert to 3d-force-graph format
        nodes = [{"id": n, "group": d.get("group", "unknown")} for n, d in graph.nodes(data=True)]
        links = [{"source": u, "target": v, "type": d.get("type", ""), "circular": d.get("circular", False)} for u, v, d in graph.edges(data=True)]
        
        return {"nodes": nodes, "links": links}
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e.stderr.decode() if e.stderr else str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)
