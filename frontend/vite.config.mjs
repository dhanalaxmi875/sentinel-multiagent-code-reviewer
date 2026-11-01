import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL("./dist", import.meta.url)),
  plugins: [
    {
      name: "sentinel-auth-gate",
      configureServer(server) {
        server.middlewares.use((request, response, next) => {
          const pathname = new URL(request.url || "/", "http://localhost").pathname;
          const isAppPage = pathname === "/" || pathname.startsWith("/app");
          const hasSessionCookie = (request.headers.cookie || "")
            .split(";")
            .some((cookie) => cookie.trim().startsWith("sentinel_session="));
          if (isAppPage && !hasSessionCookie) {
            response.writeHead(302, { Location: "/login" });
            response.end();
            return;
          }
          next();
        });
      },
    },
  ],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/login": "http://127.0.0.1:8000",
      "/register": "http://127.0.0.1:8000",
    },
  },
});
