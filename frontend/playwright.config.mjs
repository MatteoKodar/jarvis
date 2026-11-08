import {defineConfig} from '@playwright/test';
import path from 'node:path';
process.env.JARVIS_E2E_STOP_FILE=path.resolve('../data',`e2e-stop-${process.pid}`);
export default defineConfig({testDir:'./e2e',globalTeardown:'./e2e/teardown.mjs',workers:1,timeout:30000,use:{baseURL:'http://127.0.0.1:8765',headless:true,channel:process.env.JARVIS_E2E_CHANNEL||undefined,trace:'retain-on-failure'},webServer:{command:`"${process.env.JARVIS_PYTHON||(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python')}" ../scripts/e2e_server.py`,url:'http://127.0.0.1:8765',reuseExistingServer:false,timeout:30000}});
