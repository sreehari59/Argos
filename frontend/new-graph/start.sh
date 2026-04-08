#!/bin/bash

echo "=========================================="
echo "Supply Chain Knowledge Graph"
echo "=========================================="
echo ""
echo "Starting HTTP server on port 8765..."
echo ""
echo "Open your browser and go to:"
echo "  http://localhost:8765/knowledge-graph.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m http.server 8765
