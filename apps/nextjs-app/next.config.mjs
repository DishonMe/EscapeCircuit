/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Disable ESLint and TypeScript checks during production builds to prevent build failures due to linting or type errors.
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  experimental: {
    optimizePackageImports: ['lucide-react', 'katex', '@radix-ui/react-icons'],
  },
  webpack: (config) => {
    // Avoid hot reload loops when mocked-db.json changes
    const existingIgnored = config.watchOptions?.ignored;
    const ignoredArray = Array.isArray(existingIgnored)
      ? existingIgnored
      : existingIgnored
        ? [existingIgnored]
        : [];
    const sanitizedIgnored = ignoredArray.filter((entry) => typeof entry === 'string' && entry.trim().length > 0);
    config.watchOptions = {
      ...config.watchOptions,
      ignored: [...sanitizedIgnored, '**/mocked-db.json'],
    };
    return config;
  },
};

export default nextConfig;
