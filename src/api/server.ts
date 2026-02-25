import request from '@/utils/http'

export function fetchGetServerStats() {
  return request.get<Api.DataGen.ServerStats>({
    url: '/api/server/stats'
  })
}

export function fetchGetServerStatsHistory() {
  return request.get<Api.DataGen.ServerStatsHistory>({
    url: '/api/server/stats/history'
  })
}

