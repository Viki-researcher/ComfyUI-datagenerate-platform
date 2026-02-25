import request from '@/utils/http'

export function fetchCreateLog(params: Api.DataGen.LogCreateParams) {
  return request.post<any>({
    url: '/api/logs',
    params,
    showSuccessMessage: true
  })
}

export function fetchGetLogs(params: Partial<Api.DataGen.LogList> & Record<string, any>) {
  return request.get<Api.DataGen.LogList>({
    url: '/api/logs',
    params
  })
}

