import request from '@/utils/http'

export function fetchGetStats(params: {
  dimension: Api.DataGen.StatsDimension
  start_date?: string
  end_date?: string
}) {
  return request.get<any[]>({
    url: '/api/stats',
    params
  })
}

export function fetchExportStats(params: {
  dimension: Api.DataGen.StatsDimension
  start_date?: string
  end_date?: string
}) {
  // 后端返回的是文件流；当前全局 request 封装会按 JSON 解析响应体并读取 code/msg/data，
  // 因此这里先暴露一个“契约层函数”，后续页面层用“前端导出组件”从 /api/stats 数据生成 Excel。
  // 如需后端直出文件，建议为 request 增加 blob 模式。
  return request.get<any>({
    url: '/api/export',
    params
  })
}

