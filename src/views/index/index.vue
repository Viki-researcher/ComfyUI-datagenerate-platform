<!-- 布局容器 -->
<template>
  <div class="app-layout">
    <aside id="app-sidebar">
      <!-- 侧边栏菜单 -->
      <ArtSidebarMenu />
    </aside>

    <main id="app-main">
      <div id="app-header">
        <!-- 顶部导航栏 -->
        <ArtHeaderBar />
      </div>
      <div id="app-content">
        <!-- 页面内容区域（包含RouterView） -->
        <ArtPageContent />
      </div>
    </main>

    <div id="app-global">
      <ArtGlobalComponent />
    </div>
  </div>
</template>

<script setup lang="ts">
  defineOptions({ name: 'AppLayout' })
</script>

<style lang="scss" scoped>
  @use './style';
</style>
