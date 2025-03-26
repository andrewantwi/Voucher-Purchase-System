import os
import sys

def auto_git(commit_message):
    try:
        os.system("alembic revision --autogenerate")
        os.system("alembic upgrade head")
        # Add all files to the staging area
        os.system("git add .")
        # Commit with the provided commit message
        os.system(f'git commit -m "{commit_message}"')
        # Push the changes to the remote repository
        os.system("git push")
        print("Git operations completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python auto_git.py <commit-message>")
    else:
        commit_message = sys.argv[1]
        auto_git(commit_message)

