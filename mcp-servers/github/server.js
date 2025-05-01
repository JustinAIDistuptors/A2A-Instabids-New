const express = require('express');
const { MCPServer } = require('mcp-server');
const { Octokit } = require('@octokit/rest');

const app = express();
const port = 3001;

// Initialize MCP server
const mcpServer = new MCPServer({
  name: 'github-agent',
  description: 'GitHub integration for InstaBids',
  version: '1.0.0'
});

// GitHub API client
let octokit = null;

// Initialize GitHub client
mcpServer.on('init', async (params) => {
  const { token } = params;
  const githubToken = process.env.GITHUB_TOKEN || token;
  octokit = new Octokit({ auth: githubToken });
  return { status: 'success', message: 'GitHub client initialized' };
});

// Create GitHub issue
mcpServer.on('create-issue', async (params) => {
  if (!octokit) throw new Error('GitHub client not initialized');
  
  const { owner, repo, title, body } = params;
  const response = await octokit.issues.create({
    owner,
    repo,
    title,
    body
  });
  
  return response.data;
});

// Get repository details
mcpServer.on('get-repo', async (params) => {
  if (!octokit) throw new Error('GitHub client not initialized');
  
  const { owner, repo } = params;
  const response = await octokit.repos.get({
    owner,
    repo
  });
  
  return response.data;
});

  // Add git commit endpoint
mcpServer.on('commit-file', async (params) => {
  if (!octokit) throw new Error('GitHub client not initialized');
  
  const { owner, repo, path, content, branch = 'legacy-agent' } = params;
  
  // Get current head
  const { data: refData } = await octokit.git.getRef({
    owner,
    repo,
    ref: `heads/${branch}`
  });
  
  // Create blob
  const { data: blobData } = await octokit.git.createBlob({
    owner,
    repo,
    content,
    encoding: 'utf-8'
  });
  
  // Create tree
  const { data: treeData } = await octokit.git.createTree({
    owner,
    repo,
    base_tree: refData.object.sha,
    tree: [{
      path,
      mode: '100644',
      type: 'blob',
      sha: blobData.sha
    }]
  });
  
  // Create commit
  const { data: commitData } = await octokit.git.createCommit({
    owner,
    repo,
    message: `Add ${path} via MCP`,
    tree: treeData.sha,
    parents: [refData.object.sha]
  });
  
  // Update ref
  await octokit.git.updateRef({
    owner,
    repo,
    ref: `heads/${branch}`,
    sha: commitData.sha
  });
  
  return { commitUrl: commitData.html_url };
});

// Set up Express routes
app.use('/mcp', mcpServer.router);

// Start server
app.listen(port, () => {
  console.log(`GitHub MCP server running on port ${port}`);
});
