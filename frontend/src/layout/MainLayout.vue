<template>
  <div class="layout-container">
    <header class="app-header">
      <h1>DungeonClaw <span class="subtitle">(MUG Viewer)</span></h1>
      <div class="controls">
        <span class="version">v0.1.0</span>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
    <footer class="app-footer">
      <p>Server-Authoritative MUD Chunk-Crawl Spectator Plane</p>
    </footer>
  </div>
</template>

<style scoped>
.layout-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #0f111a;
  color: #e0e6ed;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #1a1d27;
  border-bottom: 1px solid #2d313f;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.app-header h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #00d2ff;
  text-shadow: 0 0 10px rgba(0, 210, 255, 0.3);
}
.subtitle {
  font-size: 1rem;
  color: #8892b0;
  font-weight: 400;
  margin-left: 0.5rem;
}
.version {
  font-size: 0.85rem;
  color: #64ffda;
  font-family: monospace;
  padding: 0.2rem 0.5rem;
  background: rgba(100, 255, 218, 0.1);
  border-radius: 4px;
}
.app-main {
  flex: 1;
  padding: 1.5rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.app-footer {
  text-align: center;
  padding: 0.75rem;
  font-size: 0.75rem;
  color: #5c677d;
  background-color: #151822;
  border-top: 1px solid #2d313f;
}
</style>
