/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: the dashboard is plain HTML/JS that any web server (or the Fenrix API itself) can host.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
