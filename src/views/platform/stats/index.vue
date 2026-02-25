<template>
  <div class="platform-stats art-full-height">
    <ElCard class="mb-3" shadow="never">
      <div class="flex-cb flex-wrap gap-2">
        <div>
          <div class="text-lg font-semibold">数据统计</div>
          <div class="text-sm text-gray-500">按天/项目/用户聚合生成次数</div>
        </div>
        <ElButton @click="loadStats" :loading="loading" v-ripple>刷新</ElButton>
      </div>
    </ElCard>

    <ElCard class="mb-3" shadow="never">
      <ArtSearchBar
        v-model="filters"
        :items="filterItems"
        :showExpand="false"
        @search="loadStats"
        @reset="resetFilters"
      />
    </ElCard>

    <ElRow :gutter="12">
      <ElCol :xs="24" :md="14">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">趋势图</div>
          </template>
          <ArtLineChart
            v-if="filters.dimension === 'day'"
            :loading="loading"
            :xAxisData="xAxis"
            :data="series"
            height="320px"
            :showAreaColor="true"
          />
          <ElEmpty v-else description="当前维度仅展示表格" />
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :md="10">
        <ElCard shadow="never" class="h-full">
          <template #header>
            <div class="font-semibold">统计结果</div>
          </template>
          <ElTable :data="tableData" v-loading="loading" height="320">
            <ElTableColumn prop="key" label="维度" />
            <ElTableColumn prop="count" label="次数" width="100" />
          </ElTable>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
  import { fetchGetStats } from '@/api/stats'

  defineOptions({ name: 'PlatformStats' })

  const loading = ref(false)

  const filters = ref<{
    dimension: Api.DataGen.StatsDimension
    start_date?: string
    end_date?: string
  }>({
    dimension: 'day',
    start_date: undefined,
    end_date: undefined
  })

  const filterItems = computed(() => [
    {
      key: 'dimension',
      label: '维度',
      type: 'select',
      props: {
        placeholder: '请选择',
        options: [
          { label: '按天', value: 'day' },
          { label: '按项目', value: 'project' },
          { label: '按用户', value: 'user' }
        ]
      },
      span: 6
    },
    { key: 'start_date', label: '开始日期', type: 'date', props: { type: 'date' }, span: 6 },
    { key: 'end_date', label: '结束日期', type: 'date', props: { type: 'date' }, span: 6 }
  ])

  const raw = ref<any[]>([])

  const loadStats = async () => {
    loading.value = true
    try {
      raw.value = await fetchGetStats({
        dimension: filters.value.dimension,
        start_date: filters.value.start_date,
        end_date: filters.value.end_date
      })
    } finally {
      loading.value = false
    }
  }

  onMounted(loadStats)

  const resetFilters = () => {
    filters.value = { dimension: 'day', start_date: undefined, end_date: undefined }
    loadStats()
  }

  const tableData = computed(() => {
    if (filters.value.dimension === 'day') {
      return (raw.value || []).map((i: any) => ({ key: i.date, count: i.count }))
    }
    if (filters.value.dimension === 'project') {
      return (raw.value || []).map((i: any) => ({ key: i.project_name ? `项目 ${i.project_name}` : `项目 ${i.project_id}`, count: i.count }))
    }
    if (filters.value.dimension === 'user') {
      return (raw.value || []).map((i: any) => ({ key: i.user_name ? `用户 ${i.user_name}` : `用户 ${i.user_id}`, count: i.count }))
    }
    return []
  })

  const xAxis = computed(() => tableData.value.map((i) => i.key))
  const series = computed(() => tableData.value.map((i) => i.count))
</script>

<style scoped>
  .platform-stats {
    padding: 12px;
  }
</style>

