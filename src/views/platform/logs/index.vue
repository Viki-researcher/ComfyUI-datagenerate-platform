<template>
  <div class="platform-logs art-full-height">
    <ArtSearchBar
      v-model="searchForm"
      :items="searchItems"
      :showExpand="false"
      @search="handleSearch"
      @reset="resetSearchParams"
    />

    <ElCard class="art-table-card" shadow="never">
      <ArtTableHeader :loading="loading" v-model:columns="columnChecks" @refresh="refreshData">
        <template #left>
          <div class="font-semibold">生成日志</div>
        </template>
      </ArtTableHeader>

      <ArtTable
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      />
    </ElCard>
  </div>
</template>

<script setup lang="ts">
  import { useTable } from '@/hooks/core/useTable'
  import { fetchGetLogs } from '@/api/logs'
  import type { ColumnOption } from '@/types/component'

  defineOptions({ name: 'PlatformLogs' })

  const searchForm = ref<Record<string, any>>({
    user_id: undefined,
    project_id: undefined,
    status: undefined,
    start: undefined,
    end: undefined
  })

  const searchItems = computed(() => [
    { key: 'user_id', label: '用户ID', type: 'number', props: { placeholder: '可选' }, span: 6 },
    { key: 'project_id', label: '项目ID', type: 'number', props: { placeholder: '可选' }, span: 6 },
    { key: 'status', label: '状态', type: 'input', props: { placeholder: '成功/失败' }, span: 6 },
    {
      key: 'start',
      label: '开始',
      type: 'date',
      props: { type: 'date', placeholder: '开始日期' },
      span: 6
    },
    { key: 'end', label: '结束', type: 'date', props: { type: 'date', placeholder: '结束日期' }, span: 6 }
  ])

  const columnsFactory = (): ColumnOption<Api.DataGen.LogListItem>[] => [
    { type: 'index', width: 60, label: '序号' },
    { prop: 'timestamp', label: '时间', width: 170, sortable: true },
    { prop: 'user', label: '用户', width: 140 },
    { prop: 'project', label: '项目', minWidth: 160 },
    { prop: 'status', label: '状态', width: 100 },
    { prop: 'concurrent_id', label: '并发ID', width: 120 },
    { prop: 'details', label: '详情', minWidth: 260 }
  ]

  const {
    columns,
    columnChecks,
    data,
    loading,
    pagination,
    getData,
    searchParams,
    resetSearchParams,
    handleSizeChange,
    handleCurrentChange,
    refreshData
  } = useTable({
    core: {
      apiFn: fetchGetLogs as any,
      apiParams: {
        current: 1,
        size: 20,
        ...searchForm.value
      },
      columnsFactory
    }
  })

  const handleSearch = (params: Record<string, any>) => {
    Object.assign(searchParams, params)
    getData()
  }
</script>

<style scoped>
  .platform-logs {
    padding: 12px;
  }
</style>

