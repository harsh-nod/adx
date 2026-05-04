<script setup>
import DefaultTheme from "vitepress/theme";
const { Layout } = DefaultTheme;
</script>

<template>
  <div class="pre-release-banner">
    Alpha release. Install with <code>pip install adx</code>. APIs may change before v1.0.
    <a href="/adx/community/roadmap">Roadmap &rarr;</a>
  </div>
  <Layout />
</template>
