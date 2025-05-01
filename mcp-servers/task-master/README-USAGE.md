# Task Master Usage Guide

This guide provides simple instructions for using Task Master to manage your project tasks.

## Quick Start

We've created a simple batch file to make using Task Master easier. Just open a Command Prompt and run:

```
cd C:\Users\Not John Or Justin\Documents\GitHub\A2A-Instabids\mcp-servers\task-master
task-master help
```

This will show you all available commands.

## Available Commands

### List all tasks

```
task-master list
```

### Show details of a specific task

```
task-master show 1
```

Replace `1` with the ID of the task you want to view.

### Add a new task

```
task-master add "Task Title" "Task Description" high
```

The priority can be `low`, `medium`, or `high`.

### Expand a task into subtasks

```
task-master expand 1 5
```

This expands task ID 1 into 5 subtasks.

### Update the status of a task

```
task-master status 1 in-progress
```

Valid status values are `pending`, `in-progress`, and `done`.

## Troubleshooting

If you encounter errors:

1. Make sure your ANTHROPIC_API_KEY is valid in the `.env` file
2. Check that task-master-ai is installed correctly
3. Verify that the tasks.json file exists and is valid
4. Try running the command with fewer arguments

## Task Structure

Tasks are stored in `tasks/tasks.json` and individual task files are generated in the `tasks` directory.

Each task has:
- ID and title
- Description
- Detailed steps
- Dependencies
- Priority
- Status (pending, in-progress, done)
- Test strategy

Subtasks are referenced using the format `taskId.subtaskId`. For example, `1.2` refers to subtask 2 of task 1.

## Example Workflow

1. List all tasks to see what's available:
   ```
   task-master list
   ```

2. View details of a specific task:
   ```
   task-master show 1
   ```

3. Start working on a task:
   ```
   task-master status 1 in-progress
   ```

4. Mark a task as complete:
   ```
   task-master status 1 done
   ```

5. Add a new task:
   ```
   task-master add "Implement Feature X" "Create the X feature with Y capabilities" high
   ```

6. Expand a task into subtasks:
   ```
   task-master expand 2 4
   ```

7. Mark a subtask as complete:
   ```
   task-master status 2.1 done
   ```
