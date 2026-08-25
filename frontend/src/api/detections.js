import { apiClient } from './client';

export const fetchDetections = async ({ jobId, eventType, limit = 50, offset = 0 } = {}) => {
  const params = { limit, offset };
  if (jobId) params.job_id = jobId;
  if (eventType) params.event_type = eventType;
  const { data } = await apiClient.get('/api/v1/detections', { params });
  return data;
};

export const uploadVideo = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post('/api/v1/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
};

export const fetchJobStatus = async (jobId) => {
  const { data } = await apiClient.get(`/api/v1/jobs/${jobId}`);
  return data;
};

export const deleteDetection = async (detectionId) => {
  await apiClient.delete(`/api/v1/detections/${detectionId}`);
};