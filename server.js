const WebSocket = require('ws');
const http = require('http');
const express = require('express');
const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Serve static files
app.use(express.static('.'));

// Store all connections
let connections = new Set();

// WebSocket connection handling
wss.on('connection', (ws) => {
    console.log('New client connected');
    connections.add(ws);

    // Forward messages to Python client
    ws.on('message', (data) => {
        // Forward to Python client
        connections.forEach(client => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(data.toString());
            }
        });
    });

    ws.on('close', () => {
        console.log('Client disconnected');
        connections.delete(ws);
    });
});

server.listen(8080, () => {
    console.log('Server is running on port 8080');
});