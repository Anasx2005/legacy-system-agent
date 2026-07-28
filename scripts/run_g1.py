from dotenv import load_dotenv

load_dotenv()

from agents.git_versioning import commit_to_model

result = commit_to_model(
    system_id="legacy-system",
    run_id="run-002",
)

print(result)