# Codebase Graph

> Transform any GitHub repository into an interactive 3D graph that visualizes the architecture and relationships within a codebase.

## Concept

Understanding a large codebase is hard. Navigating unfamiliar code, spotting dependencies, or identifying tightly-coupled modules takes hours of manual exploration.

**Codebase Graph** solves this by parsing any GitHub repository and generating a fully interactive **3D graph** where every node is a piece of your code and every edge is a relationship between them.

## What it does

Point the tool at any public (or private) GitHub repository and it will produce a multi-level 3D graph:

| Level | Nodes | Edges |
|-------|-------|-------|
| **High** | Folders / packages | Import paths, shared dependencies |
| **Mid** | Files / modules | Imports, includes, cross-file calls |
| **Low** | Functions, classes, methods | Calls, inheritance, instantiation |

All three levels coexist in the same 3D scene. You can zoom in from the macro folder structure all the way down to individual method calls, and back out again.

## Features

- **Multi-level graph** — explore your codebase at three levels of granularity in a single view
- **3D interactive visualization** — rotate, pan, zoom, and click on any node to inspect it
- **Cross-language support** — designed to work across popular languages (Python, JavaScript/TypeScript, Java, Go, etc.)
- **Relationship edges** — dependency edges are directional and labeled so you can trace call chains
- **Filtering** — isolate a single module or folder and see only its neighborhood
- **GitHub integration** — feed it a repository URL and it fetches, clones, and parses automatically

## Planned architecture

```
GitHub URL
    │
    ▼
┌─────────────┐
│  Fetcher    │  Clone / fetch repo via GitHub API
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Parser     │  Language-aware AST parsing (tree-sitter)
└──────┬──────┘
       │  Nodes + Edges
       ▼
┌─────────────┐
│ Graph Builder│  Assemble multi-level graph model
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  3D Renderer│  Interactive 3D scene (Three.js / react-three-fiber)
└─────────────┘
```

## Tech stack (planned)

- **Parsing** — [tree-sitter](https://tree-sitter.github.io/) for language-agnostic AST extraction
- **Graph model** — [NetworkX](https://networkx.org/) (Python) for building and querying the graph
- **3D visualization** — [Three.js](https://threejs.org/) / [react-three-fiber](https://docs.pmnd.rs/react-three-fiber) with [3d-force-graph](https://github.com/vasturiano/3d-force-graph)
- **Backend** — FastAPI to serve graph data as JSON
- **Frontend** — React + TypeScript

## Getting started

> Work in progress — setup instructions will be added once the first version is implemented.

## Roadmap

- [ ] Repository fetcher (GitHub URL → local clone)
- [ ] Python parser (folders → files → functions)
- [ ] Graph model builder (nodes + edges)
- [ ] REST API to expose graph data
- [ ] 3D frontend renderer
- [ ] JavaScript / TypeScript parser
- [ ] Cross-language edge detection
- [ ] Filtering and search in the 3D view
- [ ] Support for private repositories (OAuth)
- [ ] Export graph as JSON / GraphML

## License

MIT
