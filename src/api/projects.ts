import request from '@/utils/http'

export function fetchCreateProject(params: Api.DataGen.CreateProjectParams) {
  return request.post<Api.DataGen.Project>({
    url: '/api/projects',
    params,
    showSuccessMessage: true
  })
}

export function fetchGetProjects(params?: { name?: string; code?: string }) {
  return request.get<Api.DataGen.Project[]>({
    url: '/api/projects',
    params
  })
}

export function fetchUpdateProject(projectId: number, params: Partial<Pick<Api.DataGen.Project, 'name' | 'note'>>) {
  return request.put<Api.DataGen.Project>({
    url: `/api/projects/${projectId}`,
    params,
    showSuccessMessage: true
  })
}

export function fetchDeleteProject(projectId: number) {
  return request.del<void>({
    url: `/api/projects/${projectId}`,
    showSuccessMessage: true
  })
}

export function fetchOpenComfy(projectId: number) {
  return request.post<Api.DataGen.OpenComfyResponse>({
    url: `/api/projects/${projectId}/open_comfy`,
    showErrorMessage: true
  })
}

