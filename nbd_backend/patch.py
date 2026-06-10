import sys

with open("app/routes/new_chat_routes.py", "r") as f:
    content = f.read()

content = content.replace(
    '        raise HTTPException(\n            status_code=500,\n            detail=f"An unexpected error occurred: {e!s}",\n        ) from None',
    '        import traceback\n        traceback.print_exc()\n        raise HTTPException(\n            status_code=500,\n            detail=f"An unexpected error occurred: {e!s}",\n        ) from None'
)

with open("app/routes/new_chat_routes.py", "w") as f:
    f.write(content)
