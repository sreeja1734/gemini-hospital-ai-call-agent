/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Ensure the app can run properly as a standalone build in Docker
  output: "standalone",
  // Rewrite API calls to backend when running locally
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
};

export default nextConfig;
