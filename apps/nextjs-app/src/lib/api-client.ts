import { useNotifications } from '@/components/ui/notifications';
import { env } from '@/config/env';

import Cookies from 'js-cookie';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

type RequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  cookie?: string;
  params?: Record<string, string | number | boolean | undefined | null>;
  cache?: RequestCache;
  next?: NextFetchRequestConfig;
  suppressErrorNotification?: boolean;
};

function buildUrlWithParams(
  url: string,
  params?: RequestOptions['params'],
): string {
  if (!params) return url;
  const filteredParams = Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== undefined && value !== null,
    ),
  );
  if (Object.keys(filteredParams).length === 0) return url;
  const queryString = new URLSearchParams(
    filteredParams as Record<string, string>,
  ).toString();
  return `${url}?${queryString}`;
}

// Create a separate function for getting server-side cookies that can be imported where needed
export function getServerCookies() {
  if (typeof window !== 'undefined') return '';

  // Dynamic import next/headers only on server-side
  return import('next/headers').then(({ cookies }) => {
    try {
      const cookieStore = cookies();
      return cookieStore
        .getAll()
        .map((c) => `${c.name}=${c.value}`)
        .join('; ');
    } catch (error) {
      console.error('Failed to access cookies:', error);
      return '';
    }
  });
}

function getTokenFromCookieString(cookieString: string): string | undefined {
  const match = cookieString.match(new RegExp(`${AUTH_TOKEN_COOKIE_NAME}=([^;]+)`));
  return match ? match[1] : undefined;
}

async function fetchApi<T>(
  url: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    headers = {},
    body,
    cookie,
    params,
    cache = 'no-store',
    next,
    suppressErrorNotification = false,
  } = options;

  // Get cookies from the request when running on server
  let cookieHeader = cookie;
  if (typeof window === 'undefined' && !cookie) {
    cookieHeader = await getServerCookies();
  }

  // Extract auth token
  let authToken: string | undefined;
  if (typeof window !== 'undefined') {
    // Client-side: read from js-cookie
    authToken = Cookies.get(AUTH_TOKEN_COOKIE_NAME);
  } else if (cookieHeader) {
    // Server-side: parse from cookie string
    authToken = getTokenFromCookieString(cookieHeader);
  }

  const fullUrl = buildUrlWithParams(`${env.API_URL}${url}`, params);

  const maxRetries = 2;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(fullUrl, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...headers,
          ...(cookieHeader ? { Cookie: cookieHeader } : {}),
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
        credentials: 'include',
        cache,
        next,
      });

      if (!response.ok) {
        let message = '';
        try {
          const errorData = await response.json();
          message = errorData.message || errorData.detail || response.statusText;
        } catch {
          message = response.statusText || 'An error occurred';
        }
        
        if (typeof window !== 'undefined' && !suppressErrorNotification) {
          useNotifications.getState().addNotification({
            type: 'error',
            title: message || response.statusText,
          });
        }
        throw new Error(message);
      }

      return response.json();
    } catch (error) {
      if (attempt < maxRetries && error instanceof TypeError && error.message.includes('fetch')) {
        // Retry on network errors with exponential backoff
        await new Promise(resolve => setTimeout(resolve, 2 ** attempt * 1000));
        continue;
      }
      throw error;
    }
  }

  throw new Error('Request failed after retries');
}

export const api = {
  get<T>(url: string, options?: RequestOptions): Promise<T> {
    return fetchApi<T>(url, { ...options, method: 'GET' });
  },
  post<T>(url: string, body?: any, options?: RequestOptions): Promise<T> {
    return fetchApi<T>(url, { ...options, method: 'POST', body });
  },
  put<T>(url: string, body?: any, options?: RequestOptions): Promise<T> {
    return fetchApi<T>(url, { ...options, method: 'PUT', body });
  },
  patch<T>(url: string, body?: any, options?: RequestOptions): Promise<T> {
    return fetchApi<T>(url, { ...options, method: 'PATCH', body });
  },
  delete<T>(url: string, options?: RequestOptions): Promise<T> {
    return fetchApi<T>(url, { ...options, method: 'DELETE' });
  },
};
