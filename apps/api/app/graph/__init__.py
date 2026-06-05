"""Graph module — symbol extraction and dependency edge building.

Supports:
  - Python: ast-based (functions, classes, async defs, imports)
  - JavaScript/TypeScript: regex-based (function, class, const/let/var arrow fns,
    import statements, require calls)

The extractor produces:
  - Symbol records (name, kind, file, line range)
  - GraphEdge records (file A imports file B)
"""
