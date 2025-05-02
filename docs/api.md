# InstaBids API
POST /projects { description, images[] }  →  { project_id }
# example
curl -X POST localhost:8000/projects \
     -H 'Content-Type: application/json' \
     -d '{"description":"paint deck"}'