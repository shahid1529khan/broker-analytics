import { supabase } from '../lib/supabase';

// With the Vite proxy configured, /api routes are forwarded to FastAPI on port 8000.
// In production, set VITE_API_URL to your deployed backend URL.
export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = async (endpoint: string, options: RequestInit = {}) => {
  let session = null;
  try {
    const { data } = await supabase.auth.getSession();
    session = data.session;
  } catch (e) {
    console.warn('Supabase session fetch failed', e);
  }

  const token = session?.access_token;

  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Don't set Content-Type for FormData — browser sets it with boundary automatically
  if (!options.body || !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorBody = await response.text().catch(() => response.statusText);
      console.error(`API error ${response.status} on ${url}:`, errorBody);
      return null;
    }

    const contentType = response.headers.get('content-type');
    if (
      contentType &&
      (contentType.includes('application/pdf') ||
        contentType.includes('application/vnd.openxmlformats'))
    ) {
      return response.blob();
    }

    return await response.json();
  } catch (error) {
    console.error(`Network error on ${url}:`, error);
    return null;
  }
};
