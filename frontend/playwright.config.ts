import {defineConfig} from '@playwright/test';

const externalServer=process.env.PLAYWRIGHT_SKIP_WEBSERVER==='1';

export default defineConfig({
  testDir:'./tests',
  use:{baseURL:process.env.PLAYWRIGHT_BASE_URL||'http://127.0.0.1:5173'},
  webServer:externalServer?undefined:{
    command:'npm run dev',
    url:'http://127.0.0.1:5173',
    reuseExistingServer:!process.env.CI,
  },
});
