<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { fetchEventSource } from '@microsoft/fetch-event-source'

const isConnected = ref(false)
const events = ref<string[]>([])
const eventLogRef = ref<HTMLElement | null>(null)

// Simulation State
const currentChunk = ref<string>('Unknown')
const currentTick = ref<number>(0)
const grid = ref<number[][]>([])
const agents = ref<any[]>([])
const npcs = ref<any[]>([])
const floatingEvents = ref<any[]>([])

let abortController: AbortController | null = null
// lastEventId is tracked by fetchEventSource internally, but we can keep a ref if we need it for UI
const lastEventId = ref<string | null>(null)
const spectatorToken = ref<string | null>(null)

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'

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

const connectSSE = (chunkId: string = 'demo') => {
  if (abortController) {
    abortController.abort()
  }
  abortController = new AbortController()

  if (!spectatorToken.value) {
    addLog('No spectator token available. Cannot connect.')
    return
  }

  const url = `${API_BASE_URL}/v1/spectate/stream?chunk_id=${chunkId}`
  
  fetchEventSource(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${spectatorToken.value}`,
      'Accept': 'text/event-stream'
    },
    signal: abortController.signal,
    openWhenHidden: true,
    async onopen(response) {
      if (response.ok) {
        isConnected.value = true
        addLog('Connected via SSE.')
      } else {
        addLog(`Connection failed: ${response.status}`)
      }
    },
    onmessage(msg) {
      if (msg.id) {
        lastEventId.value = msg.id
      }

      try {
        const data = JSON.parse(msg.data)
        
        if (data.type === 'session_ready') {
          addLog(`Session ready.`)
        } else if (data.type === 'chunk_static') {
          currentChunk.value = data.chunk_id
          grid.value = data.grid || Array(50).fill(Array(50).fill(0))
          addLog(`Loaded static chunk layout [${data.chunk_id}]`)
        } else if (data.type === 'chunk_delta') {
          currentChunk.value = data.chunk_id
          currentTick.value = data.tick
          agents.value = data.agents || []
          npcs.value = data.npcs || []
          if (data.events && data.events.length > 0) {
            data.events.forEach((ev: any) => {
              addLog(`[Event] ${ev.type} from ${ev.from || ev.by || 'unknown'}`)
              handleFloatingEvent(ev)
            })
          }
        } else if (data.type === 'chunk_transition') {
          addLog(`Agent transition to ${data.payload?.to_chunk_id}`)
          setTimeout(() => connectSSE(data.payload?.to_chunk_id), 100)
        } else if (data.type === 'resync_required') {
          addLog(`Resync required. Fetching snapshot...`)
          fetchSnapshot(data.snapshot_url)
        }
      } catch (e) {
        console.error('Failed to parse SSE message', e)
      }
    },
    onclose() {
      if (isConnected.value) {
        isConnected.value = false
        addLog('Connection lost. Reconnecting...')
      }
    },
    onerror(err: any) {
      if (isConnected.value) {
        isConnected.value = false
        addLog(`Connection error. Retrying... ${err?.message || ''}`)
      }
      return 1000 // Retry after 1s
    }
  })
}

const fetchSnapshot = async (snapshotUrl: string) => {
  try {
    const res = await fetch(`${API_BASE_URL}${snapshotUrl}`, {
      headers: {
        'Authorization': `Bearer ${spectatorToken.value || ''}`
      }
    })
    if (res.ok) {
      const data = await res.json()
      addLog('Successfully fetched snapshot.')
      if (data.chunk_static) {
        currentChunk.value = data.chunk_static.chunk_id
        grid.value = data.chunk_static.grid || []
      }
      if (data.latest_delta) {
        currentTick.value = data.latest_delta.tick
        agents.value = data.latest_delta.agents || []
        npcs.value = data.latest_delta.npcs || []
      }
    }
  } catch (err: any) {
    addLog(`Failed to fetch snapshot for resync. ${err?.message || ''}`)
  }
}

const handleFloatingEvent = (ev: any) => {
  let targetX, targetY, type, text;

  if (ev.type === 'chat') {
    // Find agent pos
    const agent = agents.value.find(a => a.id === ev.from) || npcs.value.find(n => n.id === ev.from)
    if (agent) {
      targetX = agent.x
      targetY = agent.y
    }
    type = 'chat'
    text = ev.text
  } else if (ev.type === 'blocked') {
    targetX = ev.at?.x
    targetY = ev.at?.y
    type = 'blocked'
    text = 'BLOCKED'
  }

  if (targetX !== undefined && targetY !== undefined) {
    const eventId = Date.now() + Math.random()
    floatingEvents.value.push({
      id: eventId,
      x: targetX,
      y: targetY,
      type,
      text
    })

    // Remove after 3 seconds
    setTimeout(() => {
      floatingEvents.value = floatingEvents.value.filter(e => e.id !== eventId)
    }, 3000)
  }
}

// Quick helper
const getCellWidth = () => 100 / (grid.value[0]?.length || 50);
const getCellHeight = () => 100 / (grid.value.length || 50);

const handleCellClick = async (x: number, y: number) => {
  if (!spectatorToken.value) return;
  addLog(`Requesting move to (${x}, ${y})...`)
  
  try {
    const res = await fetch(`${API_BASE_URL}/v1/dev/agent/move-to`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${spectatorToken.value}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        agent_id: 'debug-agent',
        x,
        y
      })
    })
    
    if (res.ok) {
      const data = await res.json()
      if (data.accepted === false) {
        addLog(`Move rejected: ${data.reason}`)
        // Show as floating text
        const eventId = Date.now() + Math.random()
        floatingEvents.value.push({ id: eventId, x, y, type: 'blocked', text: `REJECTED: ${data.reason}` })
        setTimeout(() => { floatingEvents.value = floatingEvents.value.filter(e => e.id !== eventId) }, 3000)
      } else {
        addLog(`Move to (${x}, ${y}) accepted.`)
      }
    } else {
      addLog(`Move request failed: ${res.status}`)
    }
  } catch (err: any) {
    addLog(`Error moving: ${err?.message}`)
  }
}



const initSpectatorSession = async () => {
  try {
    addLog('Requesting dev spectator session token...')
    const res = await fetch(`${API_BASE_URL}/v1/dev/spectator-session`, {
      method: 'POST'
    })
    if (res.ok) {
      const data = await res.json()
      spectatorToken.value = data.token || data.session_token || data.access_token
      addLog('Session token acquired.')
      return true
    } else {
      addLog(`Failed to acquire token: ${res.status}`)
    }
  } catch (err: any) {
    addLog(`Error acquiring token: ${err?.message}`)
  }
  return false
}

onMounted(async () => {
  addLog('Initializing spectator stream...')
  const success = await initSpectatorSession()
  if (success) {
    connectSSE()
  }
})

onUnmounted(() => {
  if (abortController) {
    abortController.abort()
  }
})
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
                 :class="{ 'wall': cell === 1, 'empty': cell === 0 }"
                 @click="handleCellClick(x, y)">
            </div>
          </div>
          
          <!-- Dynamic NPC Layer (Absolute Positioning, below Agents) -->
          <div v-for="npc in npcs" :key="npc.id" 
               class="agent-marker npc-marker"
               :style="{ left: `${npc.x * getCellWidth()}%`, top: `${npc.y * getCellHeight()}%`, width: `${getCellWidth()}%`, height: `${getCellHeight()}%` }">
            <div class="agent-sprite npc-sprite"></div>
            <span class="agent-name npc-name">{{ npc.name || npc.id.substring(0,4) }}</span>
          </div>

          <!-- Dynamic Agents Layer (Absolute Positioning) -->
          <div v-for="agent in agents" :key="agent.id" 
               class="agent-marker"
               :style="{ left: `${agent.x * getCellWidth()}%`, top: `${agent.y * getCellHeight()}%`, width: `${getCellWidth()}%`, height: `${getCellHeight()}%` }">
            <div class="agent-sprite"></div>
            <span class="agent-name">{{ agent.name || agent.id.substring(0,4) }}</span>
          </div>

          <!-- Dynamic Events Layer (Absolute Positioning) -->
          <div v-for="ev in floatingEvents" :key="ev.id"
               class="floating-event"
               :class="ev.type"
               :style="{ left: `${ev.x * getCellWidth()}%`, top: `${ev.y * getCellHeight()}%` }">
            {{ ev.text }}
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
          <div class="log-scroll">
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
}
.spacer { flex: 1; }
.info-badge {
  background: rgba(255,255,255,0.05);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-family: monospace;
  color: #8892b0;
}

/* Main map and side panels */
.content-area {
  display: flex;
  gap: 1.5rem;
  flex: 1;
  min-height: 0; /* needed for nested scrolling */
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
  position: relative; /* Essential for absolute overlay layers */
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
  cursor: pointer;
}
.grid-cell:hover {
  background-color: rgba(255,255,255,0.1);
}
.grid-cell.wall {
  background-color: #2d313f;
}
.grid-cell.empty {
  background-color: transparent;
}

/* Agent & NPC rendering layer */
.agent-marker {
  position: absolute;
  transition: left 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), top 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
}
.npc-marker {
  z-index: 9; /* Render below agents if on same cell */
}
.agent-sprite {
  width: 70%;
  height: 70%;
  background-color: #00d2ff;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(0, 210, 255, 0.6);
  animation: float 2s ease-in-out infinite, pulse-glow 2s infinite alternate;
}
.npc-sprite {
  background-color: #00ff88;
  box-shadow: 0 0 10px rgba(0, 255, 136, 0.6);
  border-radius: 20%; /* different shape for npc */
  animation: float 2.5s ease-in-out infinite alternate;
}
.agent-name {
  position: absolute;
  top: -15px;
  background: rgba(0,0,0,0.6);
  padding: 1px 4px;
  border-radius: 4px;
  color: #fff;
  font-size: 0.6rem;
  font-weight: bold;
  white-space: nowrap;
}
.npc-name {
  color: #00ff88;
}

/* Floating Events */
.floating-event {
  position: absolute;
  z-index: 20;
  transform: translate(-50%, -100%);
  margin-top: -10px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: bold;
  white-space: nowrap;
  animation: float-up 3s forwards;
  pointer-events: none;
}
.floating-event.chat {
  background-color: #fff;
  color: #000;
  border: 1px solid #ccc;
  box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}
.floating-event.chat::after {
  content: '';
  position: absolute;
  bottom: -4px; left: 50%; transform: translateX(-50%);
  border-width: 4px 4px 0; border-style: solid;
  border-color: #fff transparent transparent;
}
.floating-event.blocked {
  background-color: #ff3366;
  color: #fff;
  box-shadow: 0 0 10px rgba(255, 51, 102, 0.8);
}

@keyframes pulse-glow {
  from { box-shadow: 0 0 5px rgba(0, 210, 255, 0.4); }
  to { box-shadow: 0 0 15px rgba(0, 210, 255, 1); }
}
@keyframes float-up {
  0% { transform: translate(-50%, -10px); opacity: 0; }
  10% { transform: translate(-50%, -20px); opacity: 1; }
  80% { transform: translate(-50%, -40px); opacity: 1; }
  100% { transform: translate(-50%, -50px); opacity: 0; }
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
  gap: 0.5rem;
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
