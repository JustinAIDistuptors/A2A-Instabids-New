# InstaBids API Documentation

## Projects

### Create Project

`POST /projects`

Create a new project with description and optional images.

**Request Body:**
```json
{
  "description": "string"
}
```

**Response:**
```json
{
  "project_id": "string"
}
```