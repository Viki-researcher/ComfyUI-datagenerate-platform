import App from './App.vue'
import { createApp } from 'vue'
import { initStore } from './store'                 // Store
import { initRouter } from './router'               // Router
import language from './locales'                    // 国际化
import '@styles/core/tailwind.css'                  // tailwind
import '@styles/index.scss'                         // 样式
import '@utils/sys/console.ts'                      // 控制台输出内容
import { setupGlobDirectives } from './directives'
import { setupErrorHandle } from './utils/sys/error-handle'

document.addEventListener(
  'touchstart',
  function () {},
  { passive: false }
)

const app = createApp(App)  // ① App.vue 只是“注册”，还没执行
initStore(app)
initRouter(app)   // ② 注册路由
setupGlobDirectives(app)
setupErrorHandle(app)

app.use(language)
app.mount('#app')   // ③ 开始执行 App.vue