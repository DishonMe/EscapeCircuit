import { useState } from 'react';
import { Search, Shield, User as UserIcon, Eye, Ban, UserCheck } from 'lucide-react';

interface User {
  id: string;
  username: string;
  userId: string;
  roles: ('User' | 'Creator' | 'Admin')[];
  status: 'active' | 'disabled' | 'suspended';
}

export function UsersManagement() {
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');

  // Mock user data
  const [users, setUsers] = useState<User[]>([
    {
      id: '1',
      username: 'CircuitMaster42',
      userId: 'USR-001',
      roles: ['User', 'Creator'],
      status: 'active',
    },
    {
      id: '2',
      username: 'LogicGuru',
      userId: 'USR-002',
      roles: ['User', 'Creator', 'Admin'],
      status: 'active',
    },
    {
      id: '3',
      username: 'PuzzleFan88',
      userId: 'USR-003',
      roles: ['User'],
      status: 'active',
    },
    {
      id: '4',
      username: 'SpamBot123',
      userId: 'USR-004',
      roles: ['User'],
      status: 'disabled',
    },
    {
      id: '5',
      username: 'NewbieSolver',
      userId: 'USR-005',
      roles: ['User'],
      status: 'active',
    },
  ]);

  const handleAssignCreator = (userId: string) => {
    setUsers(
      users.map((u) =>
        u.id === userId && !u.roles.includes('Creator')
          ? { ...u, roles: [...u.roles, 'Creator'] }
          : u
      )
    );
  };

  const handleRemoveCreator = (userId: string) => {
    setUsers(
      users.map((u) =>
        u.id === userId
          ? { ...u, roles: u.roles.filter((r) => r !== 'Creator') }
          : u
      )
    );
  };

  const handleToggleStatus = (userId: string) => {
    setUsers(
      users.map((u) =>
        u.id === userId
          ? { ...u, status: u.status === 'active' ? 'disabled' : 'active' }
          : u
      )
    );
  };

  // Filter users
  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      searchQuery === '' ||
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.userId.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRole =
      roleFilter === 'All' || user.roles.includes(roleFilter as any);

    const matchesStatus =
      statusFilter === 'All' || user.status === statusFilter.toLowerCase();

    return matchesSearch && matchesRole && matchesStatus;
  });

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'Admin':
        return 'bg-red-100 border-red-300 text-red-700';
      case 'Creator':
        return 'bg-purple-100 border-purple-300 text-purple-700';
      case 'User':
        return 'bg-blue-100 border-blue-300 text-blue-700';
      default:
        return 'bg-gray-100 border-gray-300 text-gray-700';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 border-green-300 text-green-700';
      case 'disabled':
        return 'bg-red-100 border-red-300 text-red-700';
      case 'suspended':
        return 'bg-yellow-100 border-yellow-300 text-yellow-700';
      default:
        return 'bg-gray-100 border-gray-300 text-gray-700';
    }
  };

  return (
    <div>
      {/* Search & Filter Controls */}
      <div className="mb-6 pb-6 border-b border-gray-300">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <label className="block text-sm text-gray-700 mb-2">
              User Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by username or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Role Filter */}
          <div>
            <label className="block text-sm text-gray-700 mb-2">
              Role Filter
            </label>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All Roles</option>
              <option value="User">User</option>
              <option value="Creator">Creator</option>
              <option value="Admin">Admin</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm text-gray-700 mb-2">
              Status Filter
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All Statuses</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users List */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-gray-900">
            Users List ({filteredUsers.length})
          </h3>
        </div>

        {filteredUsers.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p>No users found matching your filters.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredUsers.map((user) => (
              <div
                key={user.id}
                className="border border-gray-300 rounded-lg p-4 hover:border-blue-400 transition-colors"
              >
                <div className="flex items-center justify-between gap-4">
                  {/* Left: User Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <UserIcon className="w-5 h-5 text-gray-600" />
                      <h4 className="text-gray-900">{user.username}</h4>
                      <span className="text-xs text-gray-500">{user.userId}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {/* Roles */}
                      <div className="flex items-center gap-2">
                        {user.roles.map((role) => (
                          <span
                            key={role}
                            className={`px-2 py-0.5 border rounded text-xs ${getRoleBadgeColor(
                              role
                            )}`}
                          >
                            {role}
                          </span>
                        ))}
                      </div>
                      {/* Status */}
                      <span
                        className={`px-2 py-0.5 border rounded text-xs ${getStatusBadgeColor(
                          user.status
                        )}`}
                      >
                        {user.status.charAt(0).toUpperCase() + user.status.slice(1)}
                      </span>
                    </div>
                  </div>

                  {/* Right: Action Buttons */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => alert(`View profile for ${user.username}`)}
                      className="px-3 py-2 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded flex items-center gap-1 transition-colors text-sm"
                    >
                      <Eye className="w-4 h-4" />
                      View
                    </button>
                    {user.roles.includes('Creator') ? (
                      <button
                        onClick={() => handleRemoveCreator(user.id)}
                        className="px-3 py-2 bg-red-50 hover:bg-red-100 border border-red-300 rounded flex items-center gap-1 transition-colors text-sm text-red-700"
                      >
                        <Shield className="w-4 h-4" />
                        Remove Creator
                      </button>
                    ) : (
                      <button
                        onClick={() => handleAssignCreator(user.id)}
                        className="px-3 py-2 bg-purple-50 hover:bg-purple-100 border border-purple-300 rounded flex items-center gap-1 transition-colors text-sm text-purple-700"
                      >
                        <Shield className="w-4 h-4" />
                        Assign Creator
                      </button>
                    )}
                    <button
                      onClick={() => handleToggleStatus(user.id)}
                      className={`px-3 py-2 border rounded flex items-center gap-1 transition-colors text-sm ${
                        user.status === 'active'
                          ? 'bg-yellow-50 hover:bg-yellow-100 border-yellow-300 text-yellow-700'
                          : 'bg-green-50 hover:bg-green-100 border-green-300 text-green-700'
                      }`}
                    >
                      {user.status === 'active' ? (
                        <>
                          <Ban className="w-4 h-4" />
                          Disable
                        </>
                      ) : (
                        <>
                          <UserCheck className="w-4 h-4" />
                          Enable
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
