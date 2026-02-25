<template>
  <ElConfigProvider size="default" :locale="locales[language]" :z-index="3000">
    <!-- Vue Router的路由视图组件，是应用的"显示屏"，不同路由会在这里渲染不同组件；它会根据当前URL自动渲染匹配的组件 -->
    <RouterView></RouterView>
  </ElConfigProvider>
</template>

<script setup lang="ts">
  import { useUserStore } from './store/modules/user' // 用户状态管理
  import zh from 'element-plus/es/locale/lang/zh-cn' // 中文语言包
  import en from 'element-plus/es/locale/lang/en' // 英文语言包
  import { systemUpgrade } from './utils/sys' // 系统升级检查
  import { toggleTransition } from './utils/ui/animation' // 页面切换动画
  import { checkStorageCompatibility } from './utils/storage' // 存储兼容性检查
  import { initializeTheme } from './hooks/core/useTheme' // 主题初始化

  // import { useRoute } from 'vue-router'  //知道当前路由是什么
  // const route = useRoute()
  // console.log(route.fullPath, route.name, route.params, route.meta)

  // 使用用户store，获取当前语言设置
  const userStore = useUserStore()
  const { language } = storeToRefs(userStore)

  const locales = {
    zh: zh,
    en: en
  }

  // 组件挂载前执行
  onBeforeMount(() => {
    toggleTransition(true) // 开启页面切换动画
    initializeTheme() // 初始化主题（亮色/暗色）
  })

  // 组件挂载后执行
  onMounted(() => {
    checkStorageCompatibility() // 检查浏览器存储兼容性
    toggleTransition(false) // 关闭过渡动画
    systemUpgrade() // 检查系统版本更新
  })
</script>
