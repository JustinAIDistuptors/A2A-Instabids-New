#!/usr/bin/env node

import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import dotenv from 'dotenv';

// Get the directory name
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables from .env file
dotenv.config({ path: path.join(__dirname, '.env') });

// Path to the task-master.js bin file
const binPath = path.join(__dirname, 'node_modules', 'task-master-ai', 'bin', 'task-master.js');

// Check if the bin file exists
if (!fs.existsSync(binPath)) {
  console.error(`Error: Could not find task-master.js at ${binPath}`);
  console.error('Please make sure task-master-ai is installed correctly.');
  process.exit(1);
}

// Check if ANTHROPIC_API_KEY is set
if (!process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_API_KEY === 'your_anthropic_api_key_here') {
  console.error('Error: ANTHROPIC_API_KEY is not set or is using the default value.');
  console.error('Please set a valid API key in the .env file.');
  process.exit(1);
}

// Change to the project root directory
const projectRoot = path.join(__dirname, '..', '..');
process.chdir(projectRoot);
console.log(`Working directory: ${process.cwd()}`);

// Available commands
const commands = {
  list: 'List all tasks',
  show: 'Show details of a specific task',
  add: 'Add a new task',
  expand: 'Expand a task into subtasks',
  status: 'Update the status of a task',
  help: 'Show this help message'
};

// Parse command line arguments
const [,, command, ...args] = process.argv;

// Show help if no command is provided
if (!command || command === 'help') {
  console.log('Task Master Helper');
  console.log('=================');
  console.log('');
  console.log('Available commands:');
  Object.entries(commands).forEach(([cmd, desc]) => {
    console.log(`  ${cmd.padEnd(10)} ${desc}`);
  });
  console.log('');
  console.log('Examples:');
  console.log('  node task-master-helper.js list');
  console.log('  node task-master-helper.js show 1');
  console.log('  node task-master-helper.js add "Task Title" "Task Description" high');
  console.log('  node task-master-helper.js expand 1 5');
  console.log('  node task-master-helper.js status 1 in-progress');
  process.exit(0);
}

// Execute the appropriate command
try {
  let taskMasterCommand;
  let commandArgs = [];
  
  switch (command) {
    case 'list':
      taskMasterCommand = 'list';
      break;
      
    case 'show':
      if (!args[0]) {
        console.error('Error: Task ID is required for the show command.');
        console.error('Usage: node task-master-helper.js show <task_id>');
        process.exit(1);
      }
      taskMasterCommand = 'show';
      commandArgs.push(args[0]);
      break;
      
    case 'add':
      const title = args[0] || 'New Task';
      const description = args[1] || 'Task description';
      const priority = args[2] || 'medium';
      
      taskMasterCommand = 'add-task';
      commandArgs.push('--title', `"${title}"`);
      commandArgs.push('--description', `"${description}"`);
      commandArgs.push('--priority', priority);
      break;
      
    case 'expand':
      if (!args[0]) {
        console.error('Error: Task ID is required for the expand command.');
        console.error('Usage: node task-master-helper.js expand <task_id> [num_subtasks]');
        process.exit(1);
      }
      
      taskMasterCommand = 'expand';
      commandArgs.push(args[0]);
      
      if (args[1]) {
        commandArgs.push('--num', args[1]);
      }
      break;
      
    case 'status':
      if (!args[0] || !args[1]) {
        console.error('Error: Task ID and status are required for the status command.');
        console.error('Usage: node task-master-helper.js status <task_id> <status>');
        console.error('Valid status values: pending, in-progress, done');
        process.exit(1);
      }
      
      taskMasterCommand = 'set-status';
      commandArgs.push('--id', args[0]);
      commandArgs.push('--status', args[1]);
      break;
      
    default:
      console.error(`Error: Unknown command '${command}'`);
      console.error('Run "node task-master-helper.js help" to see available commands.');
      process.exit(1);
  }
  
  // Build the full command
  const fullCommand = `node "${binPath}" ${taskMasterCommand} ${commandArgs.join(' ')}`;
  console.log(`Executing: ${fullCommand}`);
  
  // Execute the command
  const result = execSync(fullCommand, {
    encoding: 'utf8',
    env: {
      ...process.env,
      ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY,
      PERPLEXITY_API_KEY: process.env.PERPLEXITY_API_KEY || '',
      MODEL: process.env.MODEL || 'claude-3-haiku-20240307',
      PERPLEXITY_MODEL: process.env.PERPLEXITY_MODEL || 'sonar-small-online',
      MAX_TOKENS: process.env.MAX_TOKENS || '64000',
      TEMPERATURE: process.env.TEMPERATURE || '0.2',
      DEFAULT_SUBTASKS: process.env.DEFAULT_SUBTASKS || '5',
      DEFAULT_PRIORITY: process.env.DEFAULT_PRIORITY || 'medium'
    }
  });
  
  console.log(result);
} catch (error) {
  console.error('Error executing command:');
  console.error(error.message);
  
  if (error.stdout) {
    console.log('\nCommand output:');
    console.log(error.stdout);
  }
  
  if (error.stderr) {
    console.log('\nError output:');
    console.log(error.stderr);
  }
  
  console.log('\nTroubleshooting tips:');
  console.log('1. Make sure your ANTHROPIC_API_KEY is valid in the .env file');
  console.log('2. Check that task-master-ai is installed correctly');
  console.log('3. Verify that the tasks.json file exists and is valid');
  console.log('4. Try running the command with fewer arguments');
  
  process.exit(1);
}
