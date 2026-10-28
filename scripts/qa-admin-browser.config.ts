import { defineConfig, devices } from '@playwright/test';
import { resolve } from 'node:path';
// Dedicated configuration: the public product suite and its trace policy remain untouched.
export default defineConfig({
 testDir:resolve('tests'),testMatch:'admin.spec.ts',timeout:240000,expect:{timeout:15000},fullyParallel:false,workers:1,retries:0,
 outputDir:resolve(process.env.QA_ADMIN_PRIVATE_DIR??'var/qa-admin-browser/unconfigured','test-output'),
 reporter:[[resolve('scripts/qa-admin-browser-reporter.ts')]],
 use:{baseURL:process.env.TEST_BASE_URL??'http://localhost:3000',trace:'off',video:'off',screenshot:'off'},
 projects:[{name:'admin-desktop',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1000}}},{name:'admin-mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}}],
});
