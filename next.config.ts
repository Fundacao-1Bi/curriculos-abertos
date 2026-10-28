import type { NextConfig } from 'next';
const config: NextConfig = {
 serverExternalPackages: ['pg'],
 outputFileTracingExcludes: {'/*':['./.env*','./data/raw/**/*','./data/extracted/**/*','./var/**/*','./.git/**/*','./output/**/*']},
 async headers() { return [{source:'/:path*',headers:[
  {key:'X-Content-Type-Options',value:'nosniff'},
  {key:'Referrer-Policy',value:'strict-origin-when-cross-origin'},
  {key:'X-Frame-Options',value:'SAMEORIGIN'},
  {key:'Permissions-Policy',value:'camera=(), microphone=(), geolocation=()'},
  {key:'Content-Security-Policy',value:"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'"}
 ]}];}
};
export default config;
