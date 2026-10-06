import { apiFetch } from './client';

export interface AuthUser {
  id: number;
  email: string;
  username: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface AuthResult {
  accessToken: string;
  user: AuthUser;
}

function fromTokenResponse(response: TokenResponse): AuthResult {
  return { accessToken: response.access_token, user: response.user };
}

export async function register(
  email: string,
  password: string,
  username: string,
): Promise<AuthResult> {
  const response = await apiFetch<TokenResponse>('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, username }),
  });
  return fromTokenResponse(response);
}

export async function login(email: string, password: string): Promise<AuthResult> {
  const response = await apiFetch<TokenResponse>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return fromTokenResponse(response);
}

export async function changePassword(
  token: string,
  currentPassword: string,
  newPassword: string,
): Promise<AuthResult> {
  const response = await apiFetch<TokenResponse>('/api/auth/change-password', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  return fromTokenResponse(response);
}

export async function logout(token: string): Promise<void> {
  await apiFetch<{ status: string }>('/api/auth/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchMe(token: string): Promise<AuthUser> {
  return apiFetch<AuthUser>('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
}
