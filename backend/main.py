import uvicorn
from routers.sync import router
from fastapi import FastAPI , Query

app = FastAPI()

app.include_router(router)


@app.get("/")
async def read_root():
    return {"message": "Hello World"}
@app.get("/sync")
async def sync(
    github_token: str = Query(..., description="The token for the GitHub API"),
    # jira_token: str = Query(..., description="The token for the Jira API"),
    # slack_token: str = Query(..., description="The token for the Slack API"),
):
    return await router.sync(github_token)

if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)