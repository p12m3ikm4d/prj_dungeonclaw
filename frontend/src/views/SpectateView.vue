<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

const isConnected = ref(false)
const events = ref<string[]>([])
const eventLogRef = ref<HTMLElement | null>(null)

// Simulation State
const currentChunk = ref<string>('Unknown')
const currentTick = ref<number>(0)
const grid = ref<number[][]>([])
const agents = ref<any[]>([])

let eventSource: EventSource | null = null

const scrollToBottom = async () => {
  await nextTick()
  if (eventLogRef.value) {
    eventLogRef.value.scrollTop = eventLogRef.value.scrollHeight
  }
}

const addLog = (msg: string) => {
  events.value.push(msg)
  if (events.value.length > 100) events.value.shift()
  scrollToBottom()
}

onMounted(() => {
  addLog('Connecting to spectator stream...')
  eventSource = new EventSource('http://localhost:3000/api/v1/spectate')
  
  eventSource.onopen = () => {
    isConnected.value = true
    addLog('Connected via SSE.')
  }

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'chunk_static') {
        currentChunk.value = data.chunk_id
        grid.value = data.grid
        addLog(`Loaded static chunk layout [${data.chunk_id}]`)
      } else if (data.type === 'chunk_delta') {
        currentChunk.value = data.chunk_id
        currentTick.value = data.tick
        agents.value = data.agents || []
        if (data.events && data.events.length > 0) {
          data.events.forEach((ev: string) => addLog(ev))
        }
      }
    } catch (e) {
      console.error('Failed to parse SSE message', e)
    }
  }

  eventSource.onerror = (e) => {
    // EventSource automatically attempts to reconnect
    if (isConnected.value) {
      isConnected.value = false
      addLog('Connection lost. Reconnecting...')
    }
  }
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})

// Quick helper to check if an agent is at a specific coordinate
const getAgentsAt = (x: number, y: number) => {
  return agents.value.filter(a => a.x === x && a.y === y)
}
</script>

<template>
  <div class="spectate-view">
    <div class="status-panel" :class="{ connected: isConnected }">
      <div class="status-indicator">
        <span class="indicator-pulse"></span>
      </div>
      <span class="status-text">{{ isConnected ? 'Connected via SSE' : 'Disconnected / Reconnecting' }}</span>
      <div class="spacer"></div>
      <span class="info-badge">Chunk: {{ currentChunk }}</span>
      <span class="info-badge">Tick: {{ currentTick }}</span>
    </div>
    
    <div class="content-area">
      <div class="map-container">
        <div v-if="grid.length > 0" class="world-grid">
          <div v-for="(row, y) in grid" :key="`row-${y}`" class="grid-row">
            <div v-for="(cell, x) in row" :key="`cell-${x}-${y}`" 
                 class="grid-cell" 
                 :class="{ 'wall': cell === 1, 'empty': cell === 0 }">
                 <!-- Render Agents inside cell -->
                 <div v-if="getAgentsAt(x, y).length > 0" class="agent-marker"></div>
            </div>
          </div>
        </div>
        <div v-else class="placeholder-map">
          Waiting for chunk data...
        </div>
      </div>
      
      <div class="side-panel">
        <div class="panel-section agent-info">
          <h3>Agent Status</h3>
          <div class="agent-stats" v-if="agents.length > 0">
            <div v-for="agent in agents" :key="agent.id" class="agent-card">
              <div class="stat"><span class="label">ID</span><span class="value">{{ agent.id }}</span></div>
              <div class="stat"><span class="label">HP</span><span class="value">{{ agent.hp }}</span></div>
              <div class="stat"><span class="label">Pos</span><span class="value">(x:{{ agent.x }}, y:{{ agent.y }})</span></div>
            </div>
          </div>
          <div class="agent-stats empty-state" v-else>
            No agents in this chunk.
          </div>
        </div>
        
        <div class="panel-section event-log">
          <h3>System Log</h3>
          <div class="log-scroll" ref="eventLogRef">
            <div v-for="(ev, idx) in events" :key="idx" class="log-item">
              <span class="log-indicator"></span>
              <span class="log-msg">{{ ev }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.spectate-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
}
/* Top Status bar */
.status-panel {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  background-color: #1a1d27;
  border-radius: 8px;
  border: 1px solid #2d313f;
  transition: all 0.3s ease;
}
.status-indicator {
  position: relative;
  width: 12px;
  height: 12px;
}
.indicator-pulse {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  border-radius: 50%;
  background-color: #ff3366;
  box-shadow: 0 0 8px #ff3366;
}
.connected .indicator-pulse {
  background-color: #00ff88;
  box-shadow: 0 0 10px #00ff88;
  animation: pulse 2s infinite cubic-bezier(0.66, 0, 0, 1);
}
@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(0, 255, 136, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
}
.status-text {
  font-weight: 500;
  font-size: 0.95rem;
  color: #ff3366;
}
.connected .status-text {
  color: #00ff88;
}
.spacer { flex: 1; }
.info-badge {
  background: rgba(255,255,255,0.05);
  padding: 0.35rem 0.85rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-family: 'Fira Code', monospace;
  color: #8892b0;
  letter-spacing: 0.5px;
  border: 1px solid rgba(255,255,255,0.1);
}

/* Main map and side panels */
.content-area {
  display: flex;
  gap: 1.5rem;
  flex: 1;
  min-height: 0;
}
.map-container {
  flex: 3;
  background-color: #0a0c12;
  border: 1px solid #2d313f;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
  padding: 1rem;
}

/* Grid Rendering */
.world-grid {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  max-width: 100vmin; /* Keep it square-ish relative to viewport */
  max-height: 100vmin;
  aspect-ratio: 1 / 1;
  background-color: #151822;
  border: 1px solid #3b4252;
}
.grid-row {
  display: flex;
  flex: 1;
}
.grid-cell {
  flex: 1;
  border-right: 1px solid rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.02);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.grid-cell.wall {
  background-color: #2d313f;
}
.grid-cell.empty {
  background-color: transparent;
}
.agent-marker {
  width: 80%;
  height: 80%;
  background-color: #00d2ff;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(0, 210, 255, 0.8);
  animation: float 2s ease-in-out infinite;
  z-index: 10;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10%); }
}

.placeholder-map {
  color: #3b4252;
  font-family: monospace;
  font-size: 1.5rem;
  letter-spacing: 2px;
}

/* Right side panel */
.side-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 300px;
}
.panel-section {
  background-color: #1a1d27;
  border: 1px solid #2d313f;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.agent-info {
  flex: 0 0 auto;
  max-height: 40%;
  overflow-y: auto;
}
.event-log {
  flex: 1;
}
.panel-section h3 {
  margin: 0;
  padding: 0.75rem 1rem;
  background-color: #232734;
  font-size: 0.95rem;
  color: #ccd6f6;
  border-bottom: 1px solid #2d313f;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.agent-stats {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.agent-card {
  background: rgba(255,255,255,0.03);
  padding: 0.75rem;
  border-radius: 6px;
  border-left: 3px solid #00d2ff;
}
.empty-state {
  color: #5c677d;
  font-size: 0.9rem;
  text-align: center;
  padding: 2rem 1rem;
}
.stat {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
}
.stat:last-child { margin-bottom: 0; }
.label { color: #8892b0; }
.value { color: #64ffda; font-family: 'Fira Code', monospace; font-weight: bold; }

.log-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  font-family: 'Fira Code', monospace;
  font-size: 0.8rem;
  background: #0f111a;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.log-item {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  padding: 0.25rem 0.5rem;
  background: rgba(255,255,255,0.02);
  border-radius: 4px;
}
.log-indicator {
  margin-top: 0.35rem;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #00d2ff;
  flex-shrink: 0;
}
.log-msg { color: #a6accd; word-break: break-all; line-height: 1.4; }
</style>
