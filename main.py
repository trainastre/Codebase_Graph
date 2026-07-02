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
    body { margin: 0; overflow: hidden; font-family: sans-serif; background-color: #000011; }
    #ui { position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(255,255,255,0.9); padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    input[type="text"] { padding: 8px; width: 300px; border: 1px solid #ccc; border-radius: 4px; }
    button { padding: 8px 15px; background-color: #0366d6; color: white; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background-color: #005cc5; }
    #loading { display: none; margin-top: 10px; color: #666; font-size: 14px; }
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
      <strong>Filters:</strong>
      <label><input type="checkbox" id="showFolders" checked onchange="applyFilters()"> Folders</label>
      <label><input type="checkbox" id="showFiles" checked onchange="applyFilters()"> Files</label>
      <label><input type="checkbox" id="showClasses" checked onchange="applyFilters()"> Classes</label>
      <label><input type="checkbox" id="showMethods" checked onchange="applyFilters()"> Methods/Functions</label>
      <label><input type="checkbox" id="showModules" checked onchange="applyFilters()"> External Modules</label>
    </div>

    <div class="legend">
      <div class="legend-item"><div class="color-box" style="background: #ffc107;"></div> Folder</div>
      <div class="legend-item"><div class="color-box" style="background: #ff5722;"></div> File</div>
      <div class="legend-item"><div class="color-box" style="background: #4caf50;"></div> Class</div>
      <div class="legend-item"><div class="color-box" style="background: #2196f3;"></div> Function/Method</div>
      <div class="legend-item"><div class="color-box" style="background: #9c27b0;"></div> External Module</div>
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

    const Graph = ForceGraph3D()
      (document.getElementById('3d-graph'))
        .nodeColor(node => colorMap[node.group] || colorMap['unknown'])
        .nodeLabel('id')
        .linkDirectionalArrowLength(3.5)
        .linkDirectionalArrowRelPos(1)
        .linkCurvature(0.1)
        .linkOpacity(0.3);

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
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        
        if (nodeIds.has(sourceId) && nodeIds.has(targetId)) {
          filteredLinks.push(l);
        } else if (nodeIds.has(targetId) && !nodeIds.has(sourceId) && l.type === 'contains') {
          const visibleAncestor = getVisibleAncestor(targetId);
          if (visibleAncestor) {
            filteredLinks.push({ source: visibleAncestor, target: targetId, type: 'contains' });
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
                    
        # Convert to 3d-force-graph format
        nodes = [{"id": n, "group": d.get("group", "unknown"), "lang": d.get("lang", "unknown")} for n, d in graph.nodes(data=True)]
        links = [{"source": u, "target": v, "type": d.get("type", "")} for u, v, d in graph.edges(data=True)]
        
        return {"nodes": nodes, "links": links}
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e.stderr.decode() if e.stderr else str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)
