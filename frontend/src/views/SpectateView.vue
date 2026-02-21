<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const isConnected = ref(false)
const events = ref<string[]>([])

onMounted(() => {
  // Placeholder for future SSE connection
  events.value.push('Ready to connect to spectator stream...')
})

</script>

<template>
  <div class="spectate-view">
    <div class="status-panel" :class="{ connected: isConnected }">
      <div class="status-indicator">
        <span class="indicator-pulse"></span>
      </div>
      <span class="status-text">{{ isConnected ? 'Connected via SSE' : 'Disconnected' }}</span>
      <div class="spacer"></div>
      <span class="info-badge">Chunk: 12_34</span>
      <span class="info-badge">Tick: 0</span>
    </div>
    
    <div class="content-area">
      <div class="map-container">
        <!-- 50x50 World Map Area -->
        <div class="placeholder-map">
          <div class="grid-overlay"></div>
          <span>[ 50x50 Simulation Area ]</span>
        </div>
      </div>
      
      <div class="side-panel">
        <div class="panel-section agent-info">
          <h3>Agent Status</h3>
          <div class="agent-stats">
            <div class="stat"><span class="label">HP</span><span class="value">100/100</span></div>
            <div class="stat"><span class="label">Pos</span><span class="value">(x:10, y:20)</span></div>
          </div>
        </div>
        
        <div class="panel-section event-log">
          <h3>System Log</h3>
          <div class="log-scroll">
            <div v-for="(ev, idx) in events" :key="idx" class="log-item">
              <span class="log-time">[{{ new Date().toLocaleTimeString() }}]</span>
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
.placeholder-map {
  color: #3b4252;
  font-family: monospace;
  font-size: 1.5rem;
  letter-spacing: 2px;
  z-index: 1;
}
.grid-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(rgba(45, 49, 63, 0.3) 1px, transparent 1px),
    linear-gradient(90deg, rgba(45, 49, 63, 0.3) 1px, transparent 1px);
  background-size: 20px 20px;
  z-index: 0;
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
.stat {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}
.label { color: #8892b0; }
.value { color: #64ffda; font-family: monospace; font-weight: bold; }

.log-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  font-family: 'Fira Code', monospace;
  font-size: 0.8rem;
  background: #0f111a;
}
.log-item {
  margin-bottom: 0.4rem;
  display: flex;
  gap: 0.5rem;
}
.log-time { color: #5c677d; }
.log-msg { color: #a6accd; }
</style>
