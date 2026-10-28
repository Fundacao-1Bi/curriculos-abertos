import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createMcpServer } from '../src/mcp/server';

// stdout é reservado exclusivamente ao transporte MCP.
const server=createMcpServer();
await server.connect(new StdioServerTransport());
for(const signal of ['SIGTERM','SIGINT'] as const)process.on(signal,()=>{void server.close().finally(()=>process.exit(0));});
