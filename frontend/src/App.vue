<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
/* Global resets */
body, html {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  background-color: #0f111a;
  color: #e0e6ed;
}
*, *::before, *::after {
  box-sizing: inherit;
}
/* Scrollbar styling for modern dark theme */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: #0f111a;
}
::-webkit-scrollbar-thumb {
  background: #2d313f;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #4a5568;
}
</style>
