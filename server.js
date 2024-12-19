const WebSocket = require('ws');
const http = require('http');
const express = require('express');
const path = require('path');
const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Serve static files from different directories
app.use(express.static('.'));  // Root directory for index.html
app.use('/static', express.static(path.join(__dirname, 'assets'))); // Assets directory
app.use('/assets', express.static(path.join(__dirname, 'assets'))); // Alternative path for assets

// Add MIME types for common asset files
app.use((req, res, next) => {
    const ext = path.extname(req.url).toLowerCase();
    switch (ext) {
        case '.png':
            res.type('image/png');
            break;
        case '.jpg':
        case '.jpeg':
            res.type('image/jpeg');
            break;
        case '.mp3':
            res.type('audio/mpeg');
            break;
        case '.wav':
            res.type('audio/wav');
            break;
        case '.ttf':
            res.type('font/ttf');
            break;
    }
    next();
});

// Store all connections
let connections = new Set();

// WebSocket connection handling
wss.on('connection', (ws) => {
    console.log('New client connected');
    connections.add(ws);

    ws.on('message', (data) => {
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

// Error handling
app.use((err, req, res, next) => {
    console.error('Error:', err);
    res.status(500).send('Internal Server Error');
});

// Start server
const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
    console.log(`Static assets served from: ${path.join(__dirname, 'assets')}`);
});