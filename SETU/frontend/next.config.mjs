/**
 * SETU frontend — static export so the whole UI can be served from any
 * plain file host (or bundled beside the API) and run fully offline.
 * All translation calls happen client-side against NEXT_PUBLIC_SETU_API.
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  reactStrictMode: true,
  trailingSlash: true,
};

export default nextConfig;
