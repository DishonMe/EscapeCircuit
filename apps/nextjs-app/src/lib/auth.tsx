import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { z } from 'zod';

import { AuthResponse, User } from '@/types/api';

import Cookies from 'js-cookie';

import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';
import { api } from './api-client';

const authCookieOptions: Cookies.CookieAttributes = {
  path: '/',
  sameSite: 'lax',
};

// api call definitions for auth (types, schemas, requests):
// these are not part of features as this is a module shared across features

export const getUser = async (): Promise<User> => {
  const response = (await api.get('/users/me', {
    suppressErrorNotification: true,
  })) as User;

  return response;
};

const userQueryKey = ['user'];

export const getUserQueryOptions = () => {
  const hasToken = typeof window !== 'undefined'
    ? !!Cookies.get(AUTH_TOKEN_COOKIE_NAME)
    : false;
  return queryOptions({
    queryKey: userQueryKey,
    queryFn: getUser,
    retry: false,
    enabled: hasToken,
  });
};

export const useUser = () => useQuery(getUserQueryOptions());

export const useLogin = ({ 
  onSuccess, 
  onError 
}: { 
  onSuccess?: () => void;
  onError?: (error: any) => void;
}) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: loginWithEmailAndPassword,
    onSuccess: (data) => {
      queryClient.setQueryData(userQueryKey, data.user);
      Cookies.set(AUTH_TOKEN_COOKIE_NAME, data.token, authCookieOptions);
      onSuccess?.();
    },
    onError: (error) => {
      onError?.(error);
    },
  });
};

export const useRegister = ({ onSuccess }: { onSuccess?: () => void }) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: registerWithEmailAndPassword,
    onSuccess: (data) => {
      queryClient.setQueryData(userQueryKey, data.user);
      Cookies.set(AUTH_TOKEN_COOKIE_NAME, data.token, authCookieOptions);
      onSuccess?.();
    },
  });
};

export const useLogout = ({ onSuccess }: { onSuccess?: () => void }) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      // Clear ALL cached queries so the next user gets fresh data
      queryClient.removeQueries();
      Cookies.remove(AUTH_TOKEN_COOKIE_NAME, { path: '/' });
      onSuccess?.();
    },
  });
};

const logout = (): Promise<void> => {
  return api.post('/users/logout');
};

export const loginInputSchema = z.object({
  username: z.string().min(1, 'Required'),
  password: z.string().min(5, 'Required'),
});

export type LoginInput = z.infer<typeof loginInputSchema>;
const loginWithEmailAndPassword = (data: LoginInput): Promise<AuthResponse> => {
  return api.post('/users/login', data, { suppressErrorNotification: true });
};

export const registerInputSchema = z.object({
  email: z.string().min(1, 'Required').email('Invalid email'),
  username: z.string().min(1, 'Required'),
  password: z.string().min(5, 'Required'),
  avatar_name: z.string().min(1, 'Avatar selection is required'),
});

export type RegisterInput = z.infer<typeof registerInputSchema>;

const registerWithEmailAndPassword = (
  data: RegisterInput,
): Promise<AuthResponse> => {
  return api.post('/users/register', data, { suppressErrorNotification: true });
};

// --- Google Login ---

const loginWithGoogle = (token: string): Promise<any> => {
  return api.post('/users/google-login', { token }, { suppressErrorNotification: true });
};

const completeGoogleRegistration = (data: {
  token: string;
  username: string;
  password: string;
}): Promise<AuthResponse> => {
  return api.post('/users/google-complete-registration', data, { suppressErrorNotification: true });
};

export const useGoogleLogin = ({
  onSuccess,
  onError,
  onNeedsPassword,
}: {
  onSuccess?: () => void;
  onError?: (error: any) => void;
  onNeedsPassword?: (data: { email: string; name: string; token: string }) => void;
}) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: loginWithGoogle,
    onSuccess: (data) => {
      // Check if this is an incomplete registration requiring password setup
      if (data.requires_password) {
        onNeedsPassword?.(data);
        return;
      }

      // Normal successful login
      queryClient.setQueryData(userQueryKey, data.user);
      Cookies.set(AUTH_TOKEN_COOKIE_NAME, data.token, authCookieOptions);
      onSuccess?.();
    },
    onError: (error) => {
      onError?.(error);
    },
  });
};

export const useCompleteGoogleRegistration = ({
  onSuccess,
  onError,
}: {
  onSuccess?: () => void;
  onError?: (error: any) => void;
}) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: completeGoogleRegistration,
    onSuccess: (data) => {
      queryClient.setQueryData(userQueryKey, data.user);
      Cookies.set(AUTH_TOKEN_COOKIE_NAME, data.token, authCookieOptions);
      onSuccess?.();
    },
    onError: (error) => {
      onError?.(error);
    },
  });
};
