import { Comment, User } from '@/types/api';

const normalizeRole = (role: string | undefined) => (role || '').toLowerCase();

export const canCreateDiscussion = (user: User | null | undefined) => {
  return normalizeRole(user?.role) === 'admin';
};
export const canDeleteDiscussion = (user: User | null | undefined) => {
  return normalizeRole(user?.role) === 'admin';
};
export const canUpdateDiscussion = (user: User | null | undefined) => {
  return normalizeRole(user?.role) === 'admin';
};

export const canViewUsers = (user: User | null | undefined) => {
  return normalizeRole(user?.role) === 'admin';
};

export const canManageUsers = (user: User | null | undefined) => {
  return normalizeRole(user?.role) === 'admin';
};

export const canManagePuzzles = (user: User | null | undefined) => {
  return normalizeRole(user?.role) === 'admin';
};

export const isPendingCreator = (user: User | null | undefined) => {
  return normalizeRole(user?.role) === 'pending_creator';
};

export const canDeleteComment = (
  user: User | null | undefined,
  comment: Comment,
) => {
  const userRole = normalizeRole(user?.role);
  if (userRole === 'admin') {
    return true;
  }

  if (userRole === 'user' && comment.author?.id === user.id) {
    return true;
  }

  return false;
};
