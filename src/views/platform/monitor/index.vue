<template>
  <div class="platform-monitor">
    <ElCard shadow="never" class="mb-3">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">服务器监控</div>
          <div class="text-sm text-gray-500">实时：CPU / 内存 / SWAP / 磁盘 / 显卡</div>
        </div>
        <div class="flex items-center gap-2">
          <ElSwitch v-model="autoRefresh" active-text="自动刷新" inactive-text="暂停" />
          <ElButton @click="load" :loading="loading" v-ripple>立即刷新</ElButton>
        </div>
      </div>
    </ElCard>

    <!-- 实时指标卡片 -->
    <ElRow :gutter="12" class="mb-3">
      <ElCol :xs="24" :sm="12" :md="6">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="flex-cb">
              <span>CPU</span>
              <span class="text-sm text-gray-500">{{ stats.cpu.toFixed(1) }}%</span>
            </div>
          </template>
          <ElProgress :percentage="stats.cpu" :stroke-width="10" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="6">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="flex-cb">
              <span>内存</span>
              <span class="text-sm text-gray-500">{{ stats.memory.toFixed(1) }}%</span>
            </div>
          </template>
          <ElProgress :percentage="stats.memory" :stroke-width="10" status="success" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="6">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="flex-cb">
              <span>SWAP</span>
              <span class="text-sm text-gray-500">{{ stats.swap.toFixed(1) }}%</span>
            </div>
          </template>
          <ElProgress :percentage="stats.swap" :stroke-width="10" status="warning" />
        </ElCard>
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="6">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="flex-cb">
              <span>磁盘</span>
              <span class="text-sm text-gray-500">{{ stats.disk.toFixed(1) }}%</span>
            </div>
          </template>
          <ElProgress :percentage="stats.disk" :stroke-width="10" status="exception" />
        </ElCard>
      </ElCol>
    </ElRow>

    <!-- 显卡信息 -->
    <ElCard shadow="never" class="mb-3" v-if="stats.gpu && stats.gpu.available">
      <template #header>
        <div class="flex-cb">
          <span>显卡 (GPU)</span>
          <ElTag type="success" size="small">已检测</ElTag>
        </div>
      </template>
      <ElRow :gutter="12">
        <ElCol
          v-for="(gpu, index) in stats.gpu.gpus"
          :key="index"
          :xs="24"
          :sm="12"
          :md="8"
        >
          <div class="gpu-card p-3 border rounded mb-3">
            <div class="font-medium mb-2">GPU {{ index }}</div>
            <div class="mb-2">
              <span class="text-gray-500">使用率：</span>
              <span class="font-medium">{{ gpu.utilization.toFixed(1) }}%</span>
            </div>
            <ElProgress
              :percentage="gpu.utilization"
              :stroke-width="8"
              status="primary"
            />
            <div class="mt-3">
              <span class="text-gray-500">显存：</span>
              <span class="font-medium">
                {{ (gpu.memory_used / 1024).toFixed(1) }} / {{ (gpu.memory_total / 1024).toFixed(1) }} GB
              </span>
            </div>
            <ElProgress
              :percentage="(gpu.memory_used / gpu.memory_total) * 100"
              :stroke-width="8"
              status="success"
            />
          </div>
        </ElCol>
      </ElRow>
    </ElCard>
    <ElCard shadow="never" class="mb-3" v-else>
      <template #header>
        <div class="flex-cb">
          <span>显卡 (GPU)</span>
          <ElTag type="info" size="small">未检测到</ElTag>
        </div>
      </template>
      <div class="text-center text-gray-400 py-4">
        <div>未检测到NVIDIA显卡或nvidia-smi不可用</div>
      </div>
    </ElCard>

    <!-- 历史曲线图 -->
    <ElCard shadow="never">
      <template #header>
        <div class="flex-cb">
          <span>资源使用趋势</span>
        </div>
      </template>
      <div ref="chartRef" class="h-64"></div>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { fetchGetServerStats } from '@/api/server'
  import * as echarts from 'echarts'

  defineOptions({ name: 'PlatformMonitor' })

  const loading = ref(false)
  const autoRefresh = ref(true)
  const chartRef = ref<HTMLElement>()
  let chartInstance: echarts.ECharts | null = null

  const showCpu = ref(true)
  const showMemory = ref(true)
  const showGpu = ref(true)

  const stats = ref<Api.DataGen.ServerStats>({
    cpu: 0,
    memory: 0,
    swap: 0,
    disk: 0,
    gpu: { available: false, gpus: [] },
    history: []
  })

  const initChart = () => {
    if (!chartRef.value) return
    chartInstance = echarts.init(chartRef.value)
    updateChart()
  }

  const updateChart = () => {
    if (!chartInstance) return

    const history = stats.value.history || []
    const timestamps = history.map((item) => {
      const date = new Date(item.timestamp * 1000)
      return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`
    })

    const series: echarts.SeriesOption[] = []

    if (showCpu.value) {
      series.push({
        name: 'CPU',
        type: 'line',
        data: history.map((item) => item.cpu),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        itemStyle: { color: '#5D87FF' },
        areaStyle: { color: 'rgba(93, 135, 255, 0.1)' }
      })
    }

    if (showMemory.value) {
      series.push({
        name: '内存',
        type: 'line',
        data: history.map((item) => item.memory),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        itemStyle: { color: '#60C041' },
        areaStyle: { color: 'rgba(96, 192, 65, 0.1)' }
      })
    }

    if (showGpu.value && stats.value.gpu && stats.value.gpu.available) {
      series.push({
        name: 'GPU',
        type: 'line',
        data: history.map((item) => item.gpu?.gpus?.[0]?.utilization || 0),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2 },
        itemStyle: { color: '#F9901F' },
        areaStyle: { color: 'rgba(249, 144, 31, 0.1)' }
      })
    }

    chartInstance.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['CPU', '内存', 'GPU'].filter((item) => {
          if (item === 'CPU') return showCpu.value
          if (item === '内存') return showMemory.value
          if (item === 'GPU') return showGpu.value && stats.value.gpu?.available
          return false
        }),
        top: 0,
        right: 0
      },
      grid: {
        left: '3%',
        right: '15%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: timestamps,
        axisLabel: {
          rotate: 0,
          interval: 'auto'
        }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%' }
      },
      series
    })
  }

  const load = async () => {
    loading.value = true
    try {
      const data = await fetchGetServerStats()
      stats.value = data
      updateChart()
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    load()
    initChart()
  })

  watch([showCpu, showMemory, showGpu], () => {
    updateChart()
  })

  let timer: number | undefined
  watch(
    autoRefresh,
    (val) => {
      if (timer) {
        clearInterval(timer)
        timer = undefined
      }
      if (val) {
        timer = window.setInterval(load, 5000)
      }
    },
    { immediate: true }
  )

  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
    if (chartInstance) {
      chartInstance.dispose()
      chartInstance = null
    }
  })
</script>

<style scoped>
  .platform-monitor {
    padding: 12px;
    overflow-y: auto;
    max-height: calc(100vh - 100px);
  }

  .gpu-card {
    background: var(--el-bg-color-page);
  }

  .h-full {
    height: 100%;
    min-height: 80px;
  }
</style>
