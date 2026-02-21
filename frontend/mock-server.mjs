import express from 'express';
import cors from 'cors';

const app = express();
app.use(cors());

// Spectate SSE Endpoint
app.get('/api/v1/spectate', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });

  // Sending initial chunk_static
  const staticData = {
    type: 'chunk_static',
    chunk_id: '12_34',
    grid: Array(50).fill(0).map(() => Array(50).fill(0).map(() => Math.random() > 0.8 ? 1 : 0)) // 0: empty, 1: wall
  };
  
  res.write(`data: ${JSON.stringify(staticData)}\n\n`);

  // Simulate tick updates with chunk_delta at 5Hz (200ms)
  let tickCounter = 0;
  const intervalId = setInterval(() => {
    tickCounter++;
    const deltaData = {
      type: 'chunk_delta',
      chunk_id: '12_34',
      tick: tickCounter,
      agents: [
        { id: 'agent_1', x: Math.floor(Math.random() * 50), y: Math.floor(Math.random() * 50), hp: 100 }
      ],
      events: []
    };
    res.write(`data: ${JSON.stringify(deltaData)}\n\n`);
  }, 200);

  req.on('close', () => {
    clearInterval(intervalId);
  });
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Mock SSE server running on http://localhost:${PORT}`);
});
